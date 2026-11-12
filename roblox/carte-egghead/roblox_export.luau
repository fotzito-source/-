--[[
	Convertit parts.json (produit par carte.py, via rendu.py) en fichiers Roblox natifs, avec Lune
	(https://lune-org.github.io).

	    lune run roblox_export.luau -- <parts.json> <dossier_sortie> [--stud-id rbxassetid://123] [--tuile 1]

	Écrit, NOM étant meta.nom (« CarteEgghead » par défaut) :
	  - NOM.rbxm (binaire) et NOM.rbxmx (XML) : le modèle de la carte (Explorer › clic droit › Insert from File…) ;
	  - NOM-demo.rbxl : une place de démonstration (carte, plein soleil tropical, StreamingEnabled, point
	    d'apparition posé sur le repère « Spawn » du dossier Reperes, ou à l'origine).

	Formes : bloc, coin, cylindre, boule, et ellipsoïde = Part de forme Block portant un SpecialMesh (MeshType Sphere,
	Scale 1, 1, 1, sans décalage) : Roblox affiche l'ellipsoïde inscrit dans la boîte de la pièce (diamètres = Size).
	Sa collision reste la boîte de la pièce. Un ellipsoïde ne reçoit jamais de studs ni de panneau.

	Pivot du modèle = origine du plan (centre de la carte, au niveau du sol) : `carte:PivotTo(CFrame.new(X, Y, Z))`.

	Studs : par défaut, les studs intégrés de Roblox (matériau Plastic + SurfaceType.Studs sur les faces concernées,
	notamment le dessus de tout le sol) : aucune image à importer, aucune instance en plus, teinte = Part.Color.
	Chaque pièce concernée porte aussi l'attribut « Studs » (faces séparées par des virgules) : le module
	Outils.AppliquerStuds peut ensuite poser une texture HD (textures/stud.png) à la place.
	Avec --stud-id, ces textures sont posées directement dans le fichier.
]]

local fs = require("@lune/fs")
local luau = require("@lune/luau")
local process = require("@lune/process")
local roblox = require("@lune/roblox")
local serde = require("@lune/serde")

local Instance = roblox.Instance
local Enum = roblox.Enum
local Vector3 = roblox.Vector3
local CFrame = roblox.CFrame
local Color3 = roblox.Color3

-- Arguments ------------------------------------------------------------------
local args = {}
for _, a in process.args do
	if a ~= "--" then
		table.insert(args, a)
	end
end
local jsonPath, outDir = args[1], args[2]
local studId, tile = nil, 1
local i = 3
while i <= #args do
	if args[i] == "--stud-id" then
		studId = args[i + 1]
		i += 2
	elseif args[i] == "--tuile" then
		tile = tonumber(args[i + 1]) :: number
		i += 2
	else
		error("argument inconnu : " .. args[i])
	end
end
assert(jsonPath and outDir, "usage : lune run roblox_export.luau -- parts.json dossier_sortie [--stud-id id] [--tuile 1]")
if studId and not string.find(studId, "://") then
	studId = "rbxassetid://" .. studId
end

local data = serde.decode("json", fs.readFile(jsonPath))
local meta = data.meta or {}
local NOM = meta.nom or "CarteEgghead"

-- Correspondances ------------------------------------------------------------
local MATERIALS = {
	SmoothPlastic = Enum.Material.SmoothPlastic,
	Plastic = Enum.Material.Plastic,
	Wood = Enum.Material.Wood,
	WoodPlanks = Enum.Material.WoodPlanks,
	Slate = Enum.Material.Slate,
	Concrete = Enum.Material.Concrete,
	Brick = Enum.Material.Brick,
	Cobblestone = Enum.Material.Cobblestone,
	Rock = Enum.Material.Rock,
	Sand = Enum.Material.Sand,
	Grass = Enum.Material.Grass,
	Fabric = Enum.Material.Fabric,
	Metal = Enum.Material.Metal,
	Neon = Enum.Material.Neon,
	Glass = Enum.Material.Glass,
}

-- Polices des panneaux (même clé que textures.py)
local FONTS = {
	rond = Enum.Font.FredokaOne,
	futur = Enum.Font.Michroma,
	sans = Enum.Font.GothamBlack,
	serif = Enum.Font.Garamond,
	brush = Enum.Font.GothamBold,
}

local SURFACES = { "TopSurface", "BottomSurface", "FrontSurface", "BackSurface", "LeftSurface", "RightSurface" }
local REPERES = "Reperes"

-- Modèles imbriqués selon le chemin de groupe « A/B/C » -------------------------
local carte = Instance.new("Model")
carte.Name = NOM
-- Pivot du modèle = origine du plan (centre de la carte, au sol) : `carte:PivotTo(CFrame.new(X, Y, Z))` pose ce
-- centre en (X, Y, Z). Sans pivot enregistré, Studio prendrait le centre de la boîte englobante.
carte.WorldPivotData = CFrame.new(0, 0, 0)
local groupCache: { [string]: any } = {}

local function groupFor(path: string)
	if path == nil or path == "" then
		return carte
	end
	local cached = groupCache[path]
	if cached then
		return cached
	end
	local parentPath, name = string.match(path, "^(.*)/([^/]+)$")
	if not name then
		parentPath, name = "", path
	end
	local parent = groupFor(parentPath :: string)
	local m = if name == REPERES then Instance.new("Folder") else Instance.new("Model")
	m.Name = name :: string
	m.Parent = parent
	groupCache[path] = m
	return m
end

local function studFaces(p): { string }
	local faces = {}
	for _, f in p.studs or {} do
		table.insert(faces, f)
	end
	-- Pente d'un WedgePart : selon les versions, elle répond à Top ou à Front.
	-- On pose les deux : la face qui n'existe pas n'affiche simplement rien.
	if p.shape == "wedge" and table.find(faces, "Top") and not table.find(faces, "Front") then
		table.insert(faces, "Front")
	end
	return faces
end

local counts = { parts = 0, ellipsoides = 0, textures = 0, labels = 0, studFaces = 0, studParts = 0, reperes = 0,
	neon = 0, verre = 0 }
-- Boîte englobante de toutes les pièces (repère du pivot), pour le résumé
local bornesMin = { math.huge, math.huge, math.huge }
local bornesMax = { -math.huge, -math.huge, -math.huge }
local repereSpawn = nil -- pièce « Spawn » du dossier Reperes (lue dans parts.json)
local nomsReperes = {}
-- Pièces attendues par groupe, dans l'ordre de parts.json : la relecture compare chaque pièce relue à sa ligne
-- (GetChildren garde l'ordre de création après sérialisation ; GetDescendants, non).
local attendusParGroupe: { [string]: { any } } = {}

for _, p in data.parts do
	local part
	if p.shape == "wedge" then
		part = Instance.new("WedgePart")
	else
		part = Instance.new("Part")
		part.Shape = if p.shape == "cyl"
			then Enum.PartType.Cylinder
			elseif p.shape == "ball" then Enum.PartType.Ball
			else Enum.PartType.Block -- bloc et ellipsoïde
	end
	part.Name = p.name
	part.Anchored = true
	part.Size = Vector3.new(p.size[1], p.size[2], p.size[3])
	local r = p.rot
	part.CFrame = CFrame.new(p.pos[1], p.pos[2], p.pos[3], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9])
	-- demi-étendue de la pièce sur chaque axe : |R| × demi-taille (boîte de la pièce)
	for a = 1, 3 do
		local h = (math.abs(r[3 * a - 2]) * p.size[1] + math.abs(r[3 * a - 1]) * p.size[2] + math.abs(r[3 * a]) * p.size[3]) / 2
		bornesMin[a] = math.min(bornesMin[a], p.pos[a] - h)
		bornesMax[a] = math.max(bornesMax[a], p.pos[a] + h)
	end
	part.Color = Color3.fromRGB(p.color[1], p.color[2], p.color[3])
	part.Material = MATERIALS[p.material] or Enum.Material.SmoothPlastic
	for _, s in SURFACES do
		(part :: any)[s] = Enum.SurfaceType.Smooth
	end
	if (p.transparency or 0) > 0 then
		part.Transparency = p.transparency
	end
	if (p.reflectance or 0) > 0 then
		part.Reflectance = p.reflectance
	end
	part.CanCollide = p.collide ~= false
	-- Repères (dossier Reperes : Spawn…) : invisibles, sans collision, détectables par .Touched et par les raycasts
	local estRepere = p.group == REPERES or string.sub(p.group or "", 1, #REPERES + 1) == REPERES .. "/"
	part.CanTouch = estRepere
	if p.collide == false and not estRepere then
		part.CanQuery = false
	end
	part.CastShadow = p.shadow ~= false
	if estRepere then
		part.Transparency = 1
		part.CanCollide = false
		part.CanTouch = true
		part.CanQuery = true
		part.CastShadow = false
		counts.reperes += 1
		table.insert(nomsReperes, p.name)
		if p.name == "Spawn" and not repereSpawn then
			repereSpawn = p
		end
	end
	for k, v in p.attrs or {} do
		part:SetAttribute(k, v)
	end

	local faces = studFaces(p)
	if p.shape == "ellipsoid" then
		assert(#faces == 0, "ellipsoïde avec studs : " .. p.name .. " (" .. (p.group or "") .. ")")
		assert(not p.label, "ellipsoïde avec panneau : " .. p.name .. " (" .. (p.group or "") .. ")")
		local mesh = Instance.new("SpecialMesh")
		mesh.Name = "Ellipsoide"
		mesh.MeshType = Enum.MeshType.Sphere
		mesh.Scale = Vector3.new(1, 1, 1)
		mesh.Offset = Vector3.new(0, 0, 0)
		mesh.Parent = part
		counts.ellipsoides += 1
	end
	if #faces > 0 then
		-- les studs intégrés passent la pièce en Plastic : un Neon ou un verre perdrait son aspect (refusé par le kit)
		assert(p.material ~= "Neon" and p.material ~= "Glass",
			("studs sur une pièce %s : %s (%s)"):format(p.material, p.name, p.group or ""))
		part:SetAttribute("Studs", table.concat(faces, ","))
		counts.studFaces += #faces
		counts.studParts += 1
		-- Studs intégrés : ils ne s'affichent que sur le matériau Plastic
		part.Material = Enum.Material.Plastic
		for _, f in faces do
			(part :: any)[f .. "Surface"] = Enum.SurfaceType.Studs
		end
		if studId then
			for _, f in faces do
				(part :: any)[f .. "Surface"] = Enum.SurfaceType.Smooth
				local t = Instance.new("Texture")
				t.Name = "Stud"
				t.Texture = studId
				t.Face = (Enum.NormalId :: any)[f]
				t.StudsPerTileU = tile
				t.StudsPerTileV = tile
				t.Parent = part
				counts.textures += 1
			end
		end
	end

	if p.label then
		local lab = p.label
		local gui = Instance.new("SurfaceGui")
		gui.Name = "Panneau"
		gui.Face = (Enum.NormalId :: any)[lab.face or "Front"]
		gui.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
		-- TextScaled plafonne la police à 100 px : pour qu'une ligne remplisse la hauteur de la face (grands
		-- panneaux), on baisse la densité de pixels quand une ligne dépasse 2,4 studs.
		local faceH = if lab.face == "Top" or lab.face == "Bottom" then p.size[3] else p.size[2]
		local nLignes = if lab.vertical then math.max(1, utf8.len(lab.text) or 1) else 1
		gui.PixelsPerStud = math.clamp(96 / (faceH / nLignes), 8, 40)
		gui.LightInfluence = if lab.glow then 0 else 1
		gui.MaxDistance = 400
		local tl = Instance.new("TextLabel")
		tl.Name = "Texte"
		tl.Size = roblox.UDim2.fromScale(1, 1)
		tl.BackgroundTransparency = if lab.bg then 0 else 1
		if lab.bg then
			tl.BackgroundColor3 = Color3.fromRGB(lab.bg[1], lab.bg[2], lab.bg[3])
		end
		tl.BorderSizePixel = 0
		local col = lab.color or { 30, 30, 40 }
		tl.TextColor3 = Color3.fromRGB(col[1], col[2], col[3])
		tl.TextScaled = true
		tl.FontFace = roblox.Font.fromEnum(FONTS[lab.font or "rond"] or Enum.Font.FredokaOne)
		local text = lab.text
		if lab.vertical then
			local chars = {}
			for _, cp in utf8.codes(text) do
				table.insert(chars, utf8.char(cp))
			end
			text = table.concat(chars, "\n")
		end
		tl.Text = text
		tl.Parent = gui
		gui.Parent = part
		counts.labels += 1
	end

	if part.Material == Enum.Material.Neon then
		counts.neon += 1
	elseif part.Material == Enum.Material.Glass then
		counts.verre += 1
	end
	part.Parent = groupFor(p.group)
	local g = p.group or ""
	attendusParGroupe[g] = attendusParGroupe[g] or {}
	table.insert(attendusParGroupe[g], {
		p = p,
		materiau = part.Material,
		transparence = part.Transparency,
		collision = part.CanCollide,
	})
	counts.parts += 1
end

-- Outils : pose des studs dans Studio -------------------------------------------
local outils = Instance.new("Folder")
outils.Name = "Outils"
outils.Parent = carte
local module = Instance.new("ModuleScript")
module.Name = "AppliquerStuds"
module.Source = ([[
--[=[
	Pose la texture « stud » sur toutes les faces marquées de la carte (attribut « Studs » ; les ellipsoïdes n'en
	ont jamais).

	1. Importez textures/stud.png (Asset Manager › Import) et copiez son identifiant.
	2. Dans la barre de commande de Studio :
	     require(workspace.NOM_CARTE.Outils.AppliquerStuds)("rbxassetid://VOTRE_ID")
	   Options : require(...)("rbxassetid://ID", { tuile = 2 })  -- studs deux fois plus gros
	             require(...)("rbxassetid://ID", { mode = "materiau" })
	   Le mode « materiau » utilise un MaterialVariant (textures/stud-colormap.png) au lieu
	   d'objets Texture : zéro instance en plus, mais studs sur toutes les faces des pièces.
	3. Relancer la commande remplace les textures déjà posées.
	4. Pour revenir aux studs intégrés de Roblox (réglage par défaut du fichier) :
	     require(workspace.NOM_CARTE.Outils.AppliquerStuds)(nil)
]=]
return function(textureId: string, options: { tuile: number?, mode: string? }?)
	local opts = options or {}
	local tuile = opts.tuile or 1
	local carte = script.Parent.Parent
	local n = 0
	local surfaces = textureId == nil
	if not surfaces and opts.mode == "materiau" then
		local ms = game:GetService("MaterialService")
		local mv = ms:FindFirstChild("StudsCarte") or Instance.new("MaterialVariant")
		mv.Name = "StudsCarte"
		mv.BaseMaterial = Enum.Material.SmoothPlastic
		mv.ColorMap = textureId
		mv.StudsPerTile = tuile
		mv.Parent = ms
	end
	for _, part in carte:GetDescendants() do
		if part:IsA("BasePart") and part:GetAttribute("Studs") then
			for _, old in part:GetChildren() do
				if old:IsA("Texture") and old.Name == "Stud" then
					old:Destroy()
				end
			end
			if surfaces then
				part.MaterialVariant = ""
				for face in string.gmatch(part:GetAttribute("Studs"), "[^,]+") do
					part[face .. "Surface"] = Enum.SurfaceType.Studs
				end
				n += 1
			elseif opts.mode == "materiau" then
				part.MaterialVariant = "StudsCarte"
				n += 1
			else
				-- la texture HD remplace les studs intégrés
				for face in string.gmatch(part:GetAttribute("Studs"), "[^,]+") do
					part[face .. "Surface"] = Enum.SurfaceType.Smooth
				end
				for face in string.gmatch(part:GetAttribute("Studs"), "[^,]+") do
					local t = Instance.new("Texture")
					t.Name = "Stud"
					t.Texture = textureId
					t.Face = Enum.NormalId[face]
					t.StudsPerTileU = tuile
					t.StudsPerTileV = tuile
					t.Parent = part
					n += 1
				end
			end
		end
	end
	print(("Carte île du futur : %d %s"):format(n, if surfaces then "pièces en studs intégrés"
		elseif opts.mode == "materiau" then "pièces en matériau stud" else "textures stud posées"))
end
]]):gsub("NOM_CARTE", NOM)
module.Parent = outils

-- Contrôle : chaque script intégré doit compiler (une erreur de syntaxe arrête l'export)
for _, s in { module } do
	local ok, err = pcall(luau.compile, s.Source)
	assert(ok, ("script %s : %s"):format(s.Name, tostring(err)))
end

assert(counts.parts > 0, "parts.json ne contient aucune pièce")
carte:SetAttribute("Version", tostring(meta.version or "1"))

-- Écriture du modèle -------------------------------------------------------------
if not fs.isDir(outDir) then
	fs.writeDir(outDir)
end
local modelPath = outDir .. "/" .. NOM .. ".rbxmx"
fs.writeFile(modelPath, roblox.serializeModel({ carte }, true))
-- version binaire, bien plus légère (même contenu)
local modelBinPath = outDir .. "/" .. NOM .. ".rbxm"
fs.writeFile(modelBinPath, roblox.serializeModel({ carte }))

-- Place de démonstration ------------------------------------------------------------
local game = Instance.new("DataModel")
local ws = game:GetService("Workspace")
local lighting = game:GetService("Lighting")

local copy = roblox.deserializeModel(fs.readFile(modelPath))[1]
copy.Parent = ws

-- Point d'apparition : sur le repère « Spawn » (bas de sa boîte, au sol ; même orientation : le joueur regarde
-- vers l'avant du repère, -Z local), sinon au centre de la carte.
local spawnCF = CFrame.new(0, 0.5, 0)
if repereSpawn then
	local r = repereSpawn.rot
	local rotation = CFrame.new(0, 0, 0, r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9])
	local bas = Vector3.new(repereSpawn.pos[1], repereSpawn.pos[2], repereSpawn.pos[3])
		- rotation.UpVector * (repereSpawn.size[2] / 2)
	spawnCF = CFrame.new(bas + rotation.UpVector * 0.5) * rotation
end
local spawn = Instance.new("SpawnLocation")
spawn.Name = "Apparition"
spawn.Anchored = true
spawn.Size = Vector3.new(10, 1, 10)
spawn.CFrame = spawnCF
spawn.Color = Color3.fromRGB(236, 242, 250)
spawn.Material = Enum.Material.SmoothPlastic
spawn.TopSurface = Enum.SurfaceType.Smooth
spawn.BottomSurface = Enum.SurfaceType.Smooth
spawn.Duration = 0
spawn.Neutral = true
spawn.Parent = ws
ws.StreamingEnabled = true
ws.ModelStreamingBehavior = Enum.ModelStreamingBehavior.Improved

-- Plein soleil tropical, couleurs saturées : soleil haut et chaud, ombres nettes, ciel cyan, air limpide.
-- Lighting.Technology est obsolète : LightingStyle + PrioritizeLightingQuality le remplacent.
lighting.LightingStyle = Enum.LightingStyle.Realistic
lighting.PrioritizeLightingQuality = true
lighting.ClockTime = 13.4
lighting.GeographicLatitude = 6
lighting.Brightness = 3.2
lighting.ExposureCompensation = 0.05
lighting.Ambient = Color3.fromRGB(96, 104, 122)
lighting.OutdoorAmbient = Color3.fromRGB(150, 168, 190)
lighting.ColorShift_Top = Color3.fromRGB(255, 244, 222)
lighting.EnvironmentDiffuseScale = 1
lighting.EnvironmentSpecularScale = 0.7
lighting.ShadowSoftness = 0.12
lighting.GlobalShadows = true

local atm = Instance.new("Atmosphere")
atm.Density = 0.24
atm.Offset = 0.15
atm.Color = Color3.fromRGB(196, 230, 255)
atm.Decay = Color3.fromRGB(96, 164, 224)
atm.Glare = 0.25
atm.Haze = 0.5
atm.Parent = lighting

local cc = Instance.new("ColorCorrectionEffect")
cc.Name = "Couleurs"
cc.Saturation = 0.22
cc.Contrast = 0.08
cc.Brightness = 0.03
cc.TintColor = Color3.fromRGB(255, 252, 246)
cc.Parent = lighting

local bloom = Instance.new("BloomEffect")
bloom.Intensity = 0.55
bloom.Size = 22
bloom.Threshold = 1.5
bloom.Parent = lighting

local rays = Instance.new("SunRaysEffect")
rays.Intensity = 0.05
rays.Spread = 0.55
rays.Parent = lighting

local placePath = outDir .. "/" .. NOM .. "-demo.rbxl"
fs.writeFile(placePath, roblox.serializePlace(game))

-- Vérification : relecture du modèle et de la place ------------------------------------
local function compter(racine)
	local nParts, nMeshes = 0, 0
	for _, d in racine:GetDescendants() do
		if d:IsA("BasePart") then
			nParts += 1
		elseif d:IsA("SpecialMesh") then
			nMeshes += 1
			local p = d.Parent
			assert(p and p.ClassName == "Part" and p.Shape == Enum.PartType.Block,
				"relecture : SpecialMesh hors d'une Part bloc (" .. d:GetFullName() .. ")")
			assert(d.MeshType == Enum.MeshType.Sphere and d.Scale == Vector3.new(1, 1, 1) and d.Offset == Vector3.new(0, 0, 0),
				"relecture : SpecialMesh mal réglé (" .. d:GetFullName() .. ")")
			assert(p:GetAttribute("Studs") == nil, "relecture : studs sur un ellipsoïde (" .. p:GetFullName() .. ")")
			for _, s in SURFACES do
				assert((p :: any)[s] == Enum.SurfaceType.Smooth, "relecture : surface stud sur un ellipsoïde")
			end
		end
	end
	return nParts, nMeshes
end

-- Chaque pièce relue, comparée à sa ligne de parts.json : classe et forme, nom, Size, CFrame (position et matrice :
-- une matrice transposée ou un axe permuté est refusé), matériau, transparence, collision, SpecialMesh, panneau.
-- Tolérances : Lune range les flottants des propriétés sur une grille de 2^-16 (≈ 1,5e-5 stud).
local FORMES = { block = Enum.PartType.Block, ellipsoid = Enum.PartType.Block, cyl = Enum.PartType.Cylinder,
	ball = Enum.PartType.Ball }
local function verifierPieces(racine, fichier: string)
	local vues = 0
	local function ecart(a: number, b: number): number
		return math.abs(a - b)
	end
	local function visiter(inst, chemin: string)
		local attendus = attendusParGroupe[chemin] or {}
		local k = 0
		for _, c in inst:GetChildren() do
			if c:IsA("BasePart") then
				k += 1
				local a = attendus[k]
				local ou = ("relecture %s : %s/%s (n° %d)"):format(fichier, chemin, c.Name, k)
				assert(a, ou .. " : pièce en trop")
				local p = a.p
				assert(c.Name == p.name, ou .. " : nom différent de " .. p.name)
				if p.shape == "wedge" then
					assert(c.ClassName == "WedgePart", ou .. " : classe " .. c.ClassName)
				else
					assert(c.ClassName == "Part" and c.Shape == FORMES[p.shape], ou .. " : forme")
				end
				local s = c.Size
				assert(ecart(s.X, p.size[1]) + ecart(s.Y, p.size[2]) + ecart(s.Z, p.size[3]) < 1e-3, ou .. " : Size")
				local cf = { c.CFrame:GetComponents() }
				for i = 1, 3 do
					assert(ecart(cf[i], p.pos[i]) < 1e-3, ou .. " : position")
				end
				for i = 1, 9 do
					assert(ecart(cf[3 + i], p.rot[i]) < 1e-4, ou .. " : rotation (composante " .. i .. ")")
				end
				assert(c.Material == a.materiau, ou .. " : matériau " .. c.Material.Name)
				assert(ecart(c.Transparency, a.transparence) < 1e-3, ou .. " : transparence")
				assert(c.CanCollide == a.collision, ou .. " : CanCollide")
				local mesh = c:FindFirstChildOfClass("SpecialMesh")
				assert((mesh ~= nil) == (p.shape == "ellipsoid"), ou .. " : SpecialMesh")
				assert((c:FindFirstChildOfClass("SurfaceGui") ~= nil) == (p.label ~= nil), ou .. " : panneau")
				vues += 1
			elseif c:IsA("Model") or c:IsA("Folder") then
				if not (inst == racine and c.Name == "Outils") then
					visiter(c, if chemin == "" then c.Name else chemin .. "/" .. c.Name)
				end
			end
		end
		assert(k == #attendus, ("relecture %s : groupe « %s » : %d pièces au lieu de %d"):format(fichier, chemin, k,
			#attendus))
	end
	visiter(racine, "")
	assert(vues == counts.parts, ("relecture %s : %d pièces comparées au lieu de %d"):format(fichier, vues, counts.parts))
end

local back = roblox.deserializeModel(fs.readFile(modelBinPath))[1]
local backXml = roblox.deserializeModel(fs.readFile(modelPath))[1]
verifierPieces(back, NOM .. ".rbxm")
verifierPieces(backXml, NOM .. ".rbxmx")
local nParts, nMeshes = compter(back)
assert(nParts == counts.parts, ("relecture .rbxm : %d pièces au lieu de %d"):format(nParts, counts.parts))
assert(nMeshes == counts.ellipsoides, ("relecture .rbxm : %d SpecialMesh au lieu de %d"):format(nMeshes, counts.ellipsoides))
local nPartsX, nMeshesX = compter(backXml)
assert(nPartsX == counts.parts and nMeshesX == counts.ellipsoides, "relecture .rbxmx : comptes différents")
local pivot = back.WorldPivotData
assert(pivot ~= nil and pivot.Position.Magnitude < 1e-6, "relecture : pivot du modèle absent ou déplacé")
-- Repères : dossier Reperes, pièces invisibles, sans collision, détectables
local dossier = back:FindFirstChild(REPERES)
assert(counts.reperes == 0 or (dossier and dossier:IsA("Folder")), "relecture : dossier Reperes absent")
if dossier then
	for _, d in dossier:GetDescendants() do
		if d:IsA("BasePart") then
			assert(d.Transparency == 1 and not d.CanCollide and d.CanTouch and d.CanQuery,
				"relecture : repère mal réglé (" .. d.Name .. ")")
		end
	end
end
assert((repereSpawn == nil) == (dossier == nil or dossier:FindFirstChild("Spawn") == nil),
	"relecture : repère Spawn incohérent")
local outilsLu = back:FindFirstChild("Outils")
local moduleLu = outilsLu and outilsLu:FindFirstChild("AppliquerStuds")
assert(moduleLu and moduleLu:IsA("ModuleScript") and moduleLu.Source == module.Source, "relecture : Outils.AppliquerStuds")

local place = roblox.deserializePlace(fs.readFile(placePath))
local wsLu = place:GetService("Workspace")
local cartePlace = wsLu:FindFirstChild(NOM)
assert(cartePlace, "relecture : carte absente de la place")
verifierPieces(cartePlace, NOM .. "-demo.rbxl")
local nPartsP, nMeshesP = compter(cartePlace)
assert(nPartsP == counts.parts and nMeshesP == counts.ellipsoides, "relecture : comptes différents dans la place")
local spawnLu = wsLu:FindFirstChild("Apparition")
assert(spawnLu and spawnLu:IsA("SpawnLocation"), "relecture : SpawnLocation absent de la place")
local posApparition = spawnLu.CFrame.Position
assert((posApparition - spawnCF.Position).Magnitude < 1e-3, "relecture : SpawnLocation déplacé")
assert(wsLu.StreamingEnabled == true, "relecture : StreamingEnabled")
local lightLu = place:GetService("Lighting")
assert(math.abs(lightLu.ClockTime - lighting.ClockTime) < 1e-3 and lightLu:FindFirstChildOfClass("Atmosphere"),
	"relecture : éclairage de la place")

print(serde.encode("json", {
	modele = modelBinPath,
	place = placePath,
	pieces = counts.parts,
	ellipsoides_specialmesh = nMeshes,
	neon = counts.neon,
	verre = counts.verre,
	pieces_a_studs = counts.studParts,
	faces_stud = counts.studFaces,
	textures_posees = counts.textures,
	panneaux = counts.labels,
	reperes = nomsReperes,
	apparition = {
		position = { posApparition.X, posApparition.Y, posApparition.Z },
		source = if repereSpawn then "Reperes/Spawn" else "origine",
	},
	pivot = { pivot.Position.X, pivot.Position.Y, pivot.Position.Z },
	emprise = { min = bornesMin, max = bornesMax },
}, false))
