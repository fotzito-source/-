--[[
	Convertit parts.json (produit par zone.py) en fichiers Roblox natifs, avec Lune (https://lune-org.github.io).

	    lune run roblox_export.luau -- <parts.json> <dossier_sortie> [--stud-id rbxassetid://123] [--tuile 1]

	Écrit :
	  - ZoneAttaqueDesTitans.rbxm (binaire) et ZoneAttaqueDesTitans.rbxmx (XML) : le modèle à insérer dans votre jeu
	    (Explorer › clic droit › Insert from File…) ;
	  - ZoneAttaqueDesTitans-demo.rbxl : une place de démonstration (zone + éclairage + point d'apparition).

	Studs : par défaut, les studs intégrés de Roblox (matériau Plastic + SurfaceType.Studs sur les
	faces concernées) : aucune image à importer, aucune instance en plus, teinte = Part.Color.
	Chaque pièce concernée porte aussi l'attribut « Studs » (faces séparées par des virgules) :
	le module Outils.AppliquerStuds peut ensuite poser une texture HD (textures/stud.png) à la place.
	Avec --stud-id, ces textures sont posées directement dans le fichier.
]]

local fs = require("@lune/fs")
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

local SURFACES = { "TopSurface", "BottomSurface", "FrontSurface", "BackSurface", "LeftSurface", "RightSurface" }

-- Modèles imbriqués selon le chemin de groupe « A/B/C » -------------------------
local zone = Instance.new("Model")
zone.Name = meta.nom or "ZoneAttaqueDesTitans"
local groupCache: { [string]: any } = {}

local function groupFor(path: string)
	if path == nil or path == "" then
		return zone
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
	local m = if name == "Reperes" then Instance.new("Folder") else Instance.new("Model")
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

local counts = { parts = 0, textures = 0, labels = 0, studFaces = 0 }

for _, p in data.parts do
	local part
	if p.shape == "wedge" then
		part = Instance.new("WedgePart")
	else
		part = Instance.new("Part")
		part.Shape = if p.shape == "cyl"
			then Enum.PartType.Cylinder
			elseif p.shape == "ball" then Enum.PartType.Ball
			else Enum.PartType.Block
	end
	part.Name = p.name
	part.Anchored = true
	part.Size = Vector3.new(p.size[1], p.size[2], p.size[3])
	local r = p.rot
	part.CFrame = CFrame.new(p.pos[1], p.pos[2], p.pos[3], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9])
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
	part.CanTouch = false
	if p.collide == false then
		part.CanQuery = false
	end
	part.CastShadow = p.shadow ~= false
	for k, v in p.attrs or {} do
		part:SetAttribute(k, v)
	end

	local faces = studFaces(p)
	if #faces > 0 then
		part:SetAttribute("Studs", table.concat(faces, ","))
		counts.studFaces += #faces
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
		gui.PixelsPerStud = 40
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
		local col = lab.color or { 30, 20, 20 }
		tl.TextColor3 = Color3.fromRGB(col[1], col[2], col[3])
		tl.TextScaled = true
		tl.FontFace = roblox.Font.fromEnum(if lab.font == "sans" then Enum.Font.GothamBlack
			elseif lab.font == "serif" then Enum.Font.Garamond
			else Enum.Font.GothamBold)
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

	part.Parent = groupFor(p.group)
	counts.parts += 1
end

-- Outils : pose des studs dans Studio -------------------------------------------
local outils = Instance.new("Folder")
outils.Name = "Outils"
outils.Parent = zone
local module = Instance.new("ModuleScript")
module.Name = "AppliquerStuds"
module.Source = [[
--[=[
	Pose la texture « stud » sur toutes les faces marquées de la zone (attribut « Studs »).

	1. Importez textures/stud.png (Asset Manager › Import) et copiez son identifiant.
	2. Dans la barre de commande de Studio :
	     require(workspace.ZoneAttaqueDesTitans.Outils.AppliquerStuds)("rbxassetid://VOTRE_ID")
	   Options : require(...)("rbxassetid://ID", { tuile = 2 })  -- studs deux fois plus gros
	             require(...)("rbxassetid://ID", { mode = "materiau" })
	   Le mode « materiau » utilise un MaterialVariant (textures/stud-colormap.png) au lieu
	   d'objets Texture : zéro instance en plus, mais studs sur toutes les faces des pièces.
	3. Relancer la commande remplace les textures déjà posées.
	4. Pour revenir aux studs intégrés de Roblox (réglage par défaut du fichier) :
	     require(workspace.ZoneAttaqueDesTitans.Outils.AppliquerStuds)(nil)
]=]
return function(textureId: string, options: { tuile: number?, mode: string? }?)
	local opts = options or {}
	local tuile = opts.tuile or 1
	local zone = script.Parent.Parent
	local n = 0
	local surfaces = textureId == nil
	if not surfaces and opts.mode == "materiau" then
		local ms = game:GetService("MaterialService")
		local mv = ms:FindFirstChild("StudsAttaqueDesTitans") or Instance.new("MaterialVariant")
		mv.Name = "StudsAttaqueDesTitans"
		mv.BaseMaterial = Enum.Material.SmoothPlastic
		mv.ColorMap = textureId
		mv.StudsPerTile = tuile
		mv.Parent = ms
	end
	for _, part in zone:GetDescendants() do
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
				part.MaterialVariant = "StudsAttaqueDesTitans"
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
	print(("Zone Attaque des Titans : %d %s"):format(n, if surfaces then "pièces en studs intégrés"
		elseif opts.mode == "materiau" then "pièces en matériau stud" else "textures stud posées"))
end
]]
module.Parent = outils

zone:SetAttribute("Version", meta.version or "1")
zone:SetAttribute("LargeurCouloir", meta.largeur_couloir or 60)
zone:SetAttribute("Longueur", meta.longueur or 400)

-- Écriture du modèle -------------------------------------------------------------
if not fs.isDir(outDir) then
	fs.writeDir(outDir)
end
local modelPath = outDir .. "/ZoneAttaqueDesTitans.rbxmx"
fs.writeFile(modelPath, roblox.serializeModel({ zone }, true))
-- version binaire, bien plus légère (même contenu)
fs.writeFile(outDir .. "/ZoneAttaqueDesTitans.rbxm", roblox.serializeModel({ zone }))

-- Place de démonstration ------------------------------------------------------------
local game = Instance.new("DataModel")
local ws = game:GetService("Workspace")
local lighting = game:GetService("Lighting")

local copy = roblox.deserializeModel(fs.readFile(modelPath))[1]
copy.Parent = ws

local spawnPos = meta.spawn or { 0, 0, 40 }
local spawn = Instance.new("SpawnLocation")
spawn.Name = "Apparition"
spawn.Anchored = true
spawn.Size = Vector3.new(12, 1, 12)
spawn.CFrame = CFrame.new(spawnPos[1], spawnPos[2] + 0.5, spawnPos[3])
spawn.Color = Color3.fromRGB(245, 205, 110)
spawn.Material = Enum.Material.SmoothPlastic
spawn.TopSurface = Enum.SurfaceType.Smooth
spawn.BottomSurface = Enum.SurfaceType.Smooth
spawn.Duration = 0
spawn.Parent = ws
ws.StreamingEnabled = true
ws.ModelStreamingBehavior = Enum.ModelStreamingBehavior.Improved

-- Éclairage réaliste (ombres nettes du soleil), ciel bleu franc : celui des rendus Blender.
-- Lighting.Technology est obsolète : LightingStyle + PrioritizeLightingQuality le remplacent.
lighting.LightingStyle = Enum.LightingStyle.Realistic
lighting.PrioritizeLightingQuality = true
lighting.ClockTime = 14.2
lighting.GeographicLatitude = 23
lighting.Brightness = 2.6
lighting.Ambient = Color3.fromRGB(88, 92, 108)
lighting.OutdoorAmbient = Color3.fromRGB(140, 146, 165)
lighting.EnvironmentDiffuseScale = 1
lighting.EnvironmentSpecularScale = 0.6
lighting.ShadowSoftness = 0.15
lighting.GlobalShadows = true

local atm = Instance.new("Atmosphere")
atm.Density = 0.27
atm.Offset = 0.12
atm.Color = Color3.fromRGB(205, 225, 255)
atm.Decay = Color3.fromRGB(120, 150, 190)
atm.Glare = 0.15
atm.Haze = 0.9
atm.Parent = lighting

local cc = Instance.new("ColorCorrectionEffect")
cc.Name = "Couleurs"
cc.Saturation = 0.12
cc.Contrast = 0.06
cc.Brightness = 0.02
cc.TintColor = Color3.fromRGB(255, 250, 242)
cc.Parent = lighting

local bloom = Instance.new("BloomEffect")
bloom.Intensity = 0.5
bloom.Size = 24
bloom.Threshold = 1.4
bloom.Parent = lighting

local rays = Instance.new("SunRaysEffect")
rays.Intensity = 0.04
rays.Spread = 0.6
rays.Parent = lighting

local placePath = outDir .. "/ZoneAttaqueDesTitans-demo.rbxl"
fs.writeFile(placePath, roblox.serializePlace(game))

-- Vérification : relecture des deux fichiers
local back = roblox.deserializeModel(fs.readFile(outDir .. "/ZoneAttaqueDesTitans.rbxm"))
local nParts = 0
for _, d in back[1]:GetDescendants() do
	if d:IsA("BasePart") then
		nParts += 1
	end
end
local place = roblox.deserializePlace(fs.readFile(placePath))
assert(nParts == counts.parts, "relecture : nombre de pièces différent")
assert(place:GetService("Workspace"):FindFirstChild(zone.Name), "relecture : zone absente de la place")

print(serde.encode("json", {
	modele = modelPath,
	place = placePath,
	pieces = counts.parts,
	faces_stud = counts.studFaces,
	textures_posees = counts.textures,
	panneaux = counts.labels,
}, false))
