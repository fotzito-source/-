--[[
	Convertit parts.json (produit par zone.py) en fichiers Roblox natifs, avec Lune (https://lune-org.github.io).

	    lune run roblox_export.luau -- <parts.json> <dossier_sortie> [--stud-id rbxassetid://123] [--tuile 1]

	Écrit :
	  - ZoneBlackClover.rbxm (binaire) et ZoneBlackClover.rbxmx (XML) : le modèle à insérer dans votre jeu
	    (Explorer › clic droit › Insert from File…) ;
	  - ZoneBlackClover-demo.rbxl : une place de démonstration (zone + éclairage + point d'apparition
	    + ambiance sombre branchée dans StarterPlayer › StarterPlayerScripts).

	Ambiance : le modèle porte ses bornes (attributs BornesMin / BornesMax, dans le repère du pivot) et
	le ModuleScript Outils.Ambiance, qui assombrit l'éclairage du joueur tant qu'il est dans la zone.
	Le LocalScript Outils.AmbianceZone8 (inactif dans le modèle) est à déplacer dans StarterPlayerScripts.

	Studs : par défaut, les studs intégrés de Roblox (matériau Plastic + SurfaceType.Studs sur les
	faces concernées) : aucune image à importer, aucune instance en plus, teinte = Part.Color.
	Chaque pièce concernée porte aussi l'attribut « Studs » (faces séparées par des virgules) :
	le module Outils.AppliquerStuds peut ensuite poser une texture HD (textures/stud.png) à la place.
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
zone.Name = meta.nom or "ZoneBlackClover"
-- Pivot du modèle = origine du plan (centre de l'entrée, au sol) : `zone:PivotTo(CFrame.new(X, Y, Z))` pose l'entrée
-- en (X, Y, Z). Sans pivot enregistré, Studio prendrait le centre de la boîte englobante.
zone.WorldPivotData = CFrame.new(0, 0, 0)
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
-- Boîte englobante de toutes les pièces, dans le repère du modèle (son pivot est l'origine du plan) :
-- elle délimite la zone pour l'ambiance (attributs BornesMin / BornesMax).
local bornesMin = { math.huge, math.huge, math.huge }
local bornesMax = { -math.huge, -math.huge, -math.huge }

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
	-- demi-étendue de la pièce sur chaque axe : |R| × demi-taille (boîte de la pièce, prudente pour cylindres et boules)
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
	-- les repères (ZoneOeufs, Entree, Sortie, Couloir) restent détectables par .Touched et par les raycasts
	local estRepere = p.group == "Reperes" or string.sub(p.group or "", 1, 8) == "Reperes/"
	part.CanTouch = estRepere
	if p.collide == false and not estRepere then
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
	     require(workspace.ZoneBlackClover.Outils.AppliquerStuds)("rbxassetid://VOTRE_ID")
	   Options : require(...)("rbxassetid://ID", { tuile = 2 })  -- studs deux fois plus gros
	             require(...)("rbxassetid://ID", { mode = "materiau" })
	   Le mode « materiau » utilise un MaterialVariant (textures/stud-colormap.png) au lieu
	   d'objets Texture : zéro instance en plus, mais studs sur toutes les faces des pièces.
	3. Relancer la commande remplace les textures déjà posées.
	4. Pour revenir aux studs intégrés de Roblox (réglage par défaut du fichier) :
	     require(workspace.ZoneBlackClover.Outils.AppliquerStuds)(nil)
]=]
return function(textureId: string, options: { tuile: number?, mode: string? }?)
	local opts = options or {}
	local tuile = opts.tuile or 1
	local zone = script.Parent.Parent
	local n = 0
	local surfaces = textureId == nil
	if not surfaces and opts.mode == "materiau" then
		local ms = game:GetService("MaterialService")
		local mv = ms:FindFirstChild("StudsZone8") or Instance.new("MaterialVariant")
		mv.Name = "StudsZone8"
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
				part.MaterialVariant = "StudsZone8"
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
	print(("Zone 8 (royaume des mages) : %d %s"):format(n, if surfaces then "pièces en studs intégrés"
		elseif opts.mode == "materiau" then "pièces en matériau stud" else "textures stud posées"))
end
]]
module.Parent = outils

-- Ambiance sombre (effet local, côté joueur) ------------------------------------------
local ambiance = Instance.new("ModuleScript")
ambiance.Name = "Ambiance"
ambiance.Source = [==[
--[=[
	Ambiance sombre de la zone, propre à chaque joueur (rien ne change sur le serveur ni chez les autres).

	Tant que le personnage est dans la zone, l'éclairage glisse vers un crépuscule violet et cramoisi ;
	dès qu'il en sort, les valeurs d'origine reviennent à l'identique.

	Branchement : le LocalScript Outils.AmbianceZone8, déplacé dans StarterPlayer › StarterPlayerScripts :
	    local zone = workspace:WaitForChild("ZoneBlackClover", math.huge)
	    require(zone:WaitForChild("Outils"):WaitForChild("Ambiance"))(zone)

	- La zone est la boîte BornesMin → BornesMax (attributs du modèle, en studs, comptés depuis son pivot :
	  le centre de l'entrée, au sol). Elle suit le modèle déplacé avec PivotTo et ne dépend pas des pièces
	  chargées (StreamingEnabled).
	- Attribut AmbianceActive du modèle à false : effet coupé, l'éclairage d'origine revient.
	- Réglages : table REGLAGES ci-dessous (seules les propriétés listées sont modifiées).
]=]

local Lighting = game:GetService("Lighting")
local Players = game:GetService("Players")
local TweenService = game:GetService("TweenService")

local REGLAGES = {
	duree = 2, -- durée du fondu (secondes)
	periode = 0.2, -- délai entre deux relevés de la position du joueur (secondes)
	marge = 6, -- pour ressortir, il faut dépasser la boîte de 6 studs : pas de clignotement en bordure
	Lighting = {
		ClockTime = 18.2, -- soleil couché
		Brightness = 1.2,
		Ambient = Color3.fromRGB(54, 36, 74),
		OutdoorAmbient = Color3.fromRGB(100, 66, 122),
	},
	Atmosphere = { -- brume violette, cramoisie à l'opposé du soleil
		Color = Color3.fromRGB(122, 84, 156),
		Decay = Color3.fromRGB(104, 34, 64),
		Density = 0.38,
		Haze = 1.8,
		Glare = 0.6,
	},
	ColorCorrectionEffect = { -- teinte ajoutée par-dessus celle du jeu
		TintColor = Color3.fromRGB(236, 212, 250),
		Brightness = -0.04,
		Contrast = 0.12,
		Saturation = 0.05,
	},
}

local INFO = TweenInfo.new(REGLAGES.duree, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut)
local suivies = {} -- zones déjà surveillées : un second appel pour la même zone ne fait rien

local function dansBoite(p: Vector3, a: Vector3, b: Vector3, m: number): boolean
	return p.X > a.X - m and p.X < b.X + m and p.Y > a.Y - m and p.Y < b.Y + m and p.Z > a.Z - m and p.Z < b.Z + m
end

return function(zone: Model?)
	local modele = zone or script.Parent.Parent :: Model
	local joueur = Players.LocalPlayer
	assert(joueur, "Ambiance : à appeler depuis un LocalScript (StarterPlayer › StarterPlayerScripts)")
	assert(modele:GetAttribute("BornesMin") and modele:GetAttribute("BornesMax"), "Ambiance : attributs BornesMin / BornesMax absents")
	if suivies[modele] then
		return
	end
	suivies[modele] = true
	local conteneur, nom = modele.Parent, modele.Name
	local dedans = false -- le joueur est-il dans la zone ?
	local enCours = {} -- fondus en cours
	local etat = nil -- nil : éclairage d'origine ; sinon { cibles, origine, crees }

	-- Anime chaque objet vers ses valeurs ; `fin` n'est appelée que si le fondu va jusqu'au bout.
	local function fondu(valeurs, fin: (() -> ())?)
		for _, t in enCours do
			t:Cancel() -- les valeurs restent où elles en sont : le fondu suivant part de là
		end
		table.clear(enCours)
		for objet, props in valeurs do
			local t = TweenService:Create(objet, INFO, props)
			table.insert(enCours, t)
			t:Play()
		end
		if fin then
			enCours[1].Completed:Connect(function(lecture)
				if lecture == Enum.PlaybackState.Completed then
					fin()
				end
			end)
		end
	end

	local function entrer()
		if not etat then
			-- Atmosphere du jeu si elle existe, sinon une nouvelle (transparente au départ) ; teinte neutre au
			-- départ. Ce qui est créé ici est détruit au retour à l'éclairage d'origine.
			local crees = {}
			local function creer(classe: string, props): Instance
				local objet = Instance.new(classe)
				objet.Name = "AmbianceZone8"
				for k, v in props do
					(objet :: any)[k] = v
				end
				objet.Parent = Lighting
				table.insert(crees, objet)
				return objet
			end
			local A = REGLAGES.Atmosphere
			local brume = Lighting:FindFirstChildOfClass("Atmosphere")
				or creer("Atmosphere", { Color = A.Color, Decay = A.Decay, Density = 0, Haze = 0, Glare = 0 })
			local teinte = creer("ColorCorrectionEffect",
				{ TintColor = Color3.new(1, 1, 1), Brightness = 0, Contrast = 0, Saturation = 0 })
			local cibles = { [Lighting] = REGLAGES.Lighting, [brume] = A, [teinte] = REGLAGES.ColorCorrectionEffect }
			local origine = {}
			for objet, props in cibles do
				origine[objet] = {}
				for k in props do
					origine[objet][k] = (objet :: any)[k]
				end
			end
			etat = { cibles = cibles, origine = origine, crees = crees }
		end
		fondu(etat.cibles)
	end

	local function sortir()
		local crees = etat.crees
		fondu(etat.origine, function()
			if not dedans then -- (l'événement peut arriver un peu après : le joueur est peut-être déjà revenu)
				for _, objet in crees do
					objet:Destroy()
				end
				etat = nil
			end
		end)
	end

	task.spawn(function()
		while true do
			-- Avec StreamingEnabled, le modèle peut être déchargé puis renvoyé (nouvelle instance) : on le retrouve.
			if not modele.Parent and conteneur then
				modele = conteneur:FindFirstChild(nom) or modele
			end
			local perso = joueur.Character -- relu à chaque relevé : suit les réapparitions
			local racine = perso and perso:FindFirstChild("HumanoidRootPart")
			if racine then
				local p = modele:GetPivot():PointToObjectSpace(racine.Position) -- position dans le repère de la zone
				local marge = if dedans then REGLAGES.marge else 0
				local ici = modele.Parent ~= nil
					and modele:GetAttribute("AmbianceActive") ~= false
					and dansBoite(p, modele:GetAttribute("BornesMin"), modele:GetAttribute("BornesMax"), marge)
				if ici ~= dedans then
					dedans = ici
					if ici then
						entrer()
					else
						sortir()
					end
				end
			end
			task.wait(REGLAGES.periode)
		end
	end)
end
]==]
ambiance.Parent = outils

-- LocalScript de lancement : inactif dans le modèle (Workspace), il sert dès qu'on le place dans StarterPlayerScripts
local lanceur = Instance.new("LocalScript")
lanceur.Name = "AmbianceZone8"
lanceur.Source = [==[
-- Ambiance sombre de la zone 8 (royaume des mages) : dans la zone, le ciel passe à un crépuscule violet et
-- cramoisi ; à la sortie, l'éclairage d'origine revient. Effet propre à chaque joueur.
-- À placer dans StarterPlayer › StarterPlayerScripts (rangé dans le modèle de la zone, il ne s'exécute pas).
-- Réglages : ModuleScript Outils.Ambiance du modèle. Couper l'effet : attribut AmbianceActive du modèle à false
-- (ou supprimer ce script). Zone renommée ou rangée dans un dossier : adaptez le chemin ci-dessous.
-- La zone est attendue sans limite de temps : avec StreamingEnabled, elle n'arrive qu'à l'approche du joueur.
local zone = workspace:WaitForChild("ZoneBlackClover", math.huge)
require(zone:WaitForChild("Outils"):WaitForChild("Ambiance"))(zone)
]==]
lanceur.Parent = outils

-- Contrôle : chaque script intégré doit compiler (une erreur de syntaxe arrête l'export)
for _, s in { module, ambiance, lanceur } do
	local ok, err = pcall(luau.compile, s.Source)
	assert(ok, ("script %s : %s"):format(s.Name, tostring(err)))
end

zone:SetAttribute("Version", meta.version or "1")
zone:SetAttribute("LargeurCouloir", meta.largeur_couloir or 60)
zone:SetAttribute("Longueur", meta.longueur or 400)
-- Bornes de la zone (repère du pivot), arrondies au dixième vers l'extérieur ; AmbianceActive = false coupe l'ambiance.
local function versBas(v: number): number
	return math.floor(v * 10 + 1e-6) / 10
end
local function versHaut(v: number): number
	return math.ceil(v * 10 - 1e-6) / 10
end
assert(counts.parts > 0, "parts.json ne contient aucune pièce")
zone:SetAttribute("BornesMin", Vector3.new(versBas(bornesMin[1]), versBas(bornesMin[2]), versBas(bornesMin[3])))
zone:SetAttribute("BornesMax", Vector3.new(versHaut(bornesMax[1]), versHaut(bornesMax[2]), versHaut(bornesMax[3])))
zone:SetAttribute("AmbianceActive", true)

-- Écriture du modèle -------------------------------------------------------------
if not fs.isDir(outDir) then
	fs.writeDir(outDir)
end
local modelPath = outDir .. "/ZoneBlackClover.rbxmx"
fs.writeFile(modelPath, roblox.serializeModel({ zone }, true))
-- version binaire, bien plus légère (même contenu)
fs.writeFile(outDir .. "/ZoneBlackClover.rbxm", roblox.serializeModel({ zone }))

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

-- Ambiance sombre : le LocalScript de lancement tourne depuis StarterPlayer › StarterPlayerScripts, comme dans
-- votre jeu ; il attend workspace.ZoneBlackClover puis appelle Outils.Ambiance.
local starterPlayer = game:GetService("StarterPlayer")
local scriptsJoueur = Instance.new("StarterPlayerScripts")
scriptsJoueur.Parent = starterPlayer
Instance.new("StarterCharacterScripts").Parent = starterPlayer
copy.Outils.AmbianceZone8:Clone().Parent = scriptsJoueur

local placePath = outDir .. "/ZoneBlackClover-demo.rbxl"
fs.writeFile(placePath, roblox.serializePlace(game))

-- Vérification : relecture des deux fichiers
local back = roblox.deserializeModel(fs.readFile(outDir .. "/ZoneBlackClover.rbxm"))
local nParts = 0
for _, d in back[1]:GetDescendants() do
	if d:IsA("BasePart") then
		nParts += 1
	end
end
local place = roblox.deserializePlace(fs.readFile(placePath))
assert(nParts == counts.parts, "relecture : nombre de pièces différent")
local zonePlace = place:GetService("Workspace"):FindFirstChild(zone.Name)
assert(zonePlace, "relecture : zone absente de la place")
local pivot = back[1].WorldPivotData
assert(pivot ~= nil and pivot.Position.Magnitude < 1e-6, "relecture : pivot du modèle absent ou déplacé")
-- ambiance : bornes, module et LocalScript relus dans le modèle et dans la place
local bmin, bmax = back[1]:GetAttribute("BornesMin"), back[1]:GetAttribute("BornesMax")
assert(typeof(bmin) == "Vector3" and typeof(bmax) == "Vector3", "relecture : attributs BornesMin / BornesMax absents")
assert(zonePlace:GetAttribute("BornesMax") == bmax, "relecture : bornes absentes de la zone de la place")
local moduleLu = back[1].Outils:FindFirstChild("Ambiance")
assert(moduleLu and moduleLu:IsA("ModuleScript") and moduleLu.Source == ambiance.Source, "relecture : module Outils.Ambiance")
local spsLu = place:GetService("StarterPlayer"):FindFirstChildOfClass("StarterPlayerScripts")
local lanceurLu = spsLu and spsLu:FindFirstChild("AmbianceZone8")
assert(lanceurLu and lanceurLu:IsA("LocalScript") and lanceurLu.Source == lanceur.Source,
	"relecture : LocalScript AmbianceZone8 absent de StarterPlayerScripts")

print(serde.encode("json", {
	modele = modelPath,
	place = placePath,
	pieces = counts.parts,
	faces_stud = counts.studFaces,
	textures_posees = counts.textures,
	panneaux = counts.labels,
	pivot = { pivot.Position.X, pivot.Position.Y, pivot.Position.Z },
	bornes = { min = { bmin.X, bmin.Y, bmin.Z }, max = { bmax.X, bmax.Y, bmax.Z } },
	ambiance = "Outils.Ambiance + StarterPlayerScripts.AmbianceZone8",
}, false))
