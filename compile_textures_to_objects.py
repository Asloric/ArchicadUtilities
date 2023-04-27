import xml.etree.ElementTree as ET
import os
import shutil

xml_folder = 'C:\\Users\\clovis.flayols\\Desktop\\Object surface converter\\surfaces XML'
xml_attribute_folder = 'C:\\Users\\clovis.flayols\\Desktop\\Object surface converter\\surfaces XML attribute'
gsm_texture_folder = 'C:\\Users\\clovis.flayols\\Desktop\\Object surface converter\\surfaces GSM\\[TImg] Textures'
cached_texture_folder = {}
objet_xml_folder = 'C:\\Users\\clovis.flayols\\Desktop\\Object surface converter\\objets XML'


#============================================================================================================================================
#============================================================================================================================================
#============================================================================================================================================

class SURFACES():
    '''Informations de représentation des surfaces dans les scripts. Script_1D compatible avec objets.'''
    instances = {}

    def __init__(self, name):
        self.name = name
        self.textures = {} #  {texture_name : texture file}
        self.preview = None
        self.surface_attribute = None # Script de propriétés de la surface tel qu'exporté par archicad. Contient l'Index.
        SURFACES.instances[name] = self
    
    @classmethod
    def load_files(cls, path):
        for file in os.scandir(path):
            if file.name.endswith(".xml"): # filtre les fichiers, et évite les surfaces de séparation
                xml_file = ET.parse(file)
                xml_data = xml_file.getroot()
                
                surface_instance = cls(file.name.replace(".xml", "")) # créé l'instance de class de la surface
                for section in xml_data:
                    setattr(surface_instance, section.tag, section) # rempli l'instance avec les attributs du xml
            
                surface_instance.find_textures()
                
                
    def print(self):
        print(surface.name)
        for attr in dir(self):
            if not callable(getattr(self, attr)) and not "__" in attr:
                print("    " + attr) #, type(getattr(self, attr)))

    def find_textures(self):
        #if hasattr(self, "Picture"):  # Pas utile pour la compilation des textures dans les objets.
        # récupere le path de la preview
            #self.prefiew = self.Picture.get("path")
            
        # Lis le script_1D et cherche les lignes file_dependance.
        script_1d = self.Script_1D.text.split("\n") # Créé une liste 
        for line in script_1d:
            if line.startswith("file_dependence"):
                texture_file_name = line.split("`")[1] # trouve le nom de la texture en assumant qu'il y ai qu'une seule texture par ligne.
                # ATTENTION!!!!  le character ` utilisé dans le xml n'est pas un 4 mais un altgr + 7
                # Check dans le dossier textures si il y a un fichier de ce nom
                
                # Créé un dict cache pour éviter d'avoir à lire toutes les textures à chaque fois.
                if not len(cached_texture_folder.keys()):
                    for file in os.scandir(gsm_texture_folder):
                        cached_texture_folder[file.name.split(".")[0]] = file
                
                # trouve la texture dans le cache
                if texture_file := cached_texture_folder.get(texture_file_name):
                    # copie le fichier dans le dossier correspondant (optionnel pour l'instant, TODO)
                    # ajoute le fichier au dict de la class
                    self.textures[texture_file_name] = texture_file

    
    def get_script_1d(self, new_material_name=None):
        script = []
        lines = self.Script_1D.text.split("\n")
        for line in lines:
            if line.startswith("<![CDATA["):
                script.append(line.replace("<![CDATA[", ""))
            elif line.startswith("call "):
                pass
            elif line.endswith("]]>"):
                script.append(line.replace("]]>", ""))
            else:
                if new_material_name:
                    if line.startswith("define material "):
                        line_parts = line.split('"')
                        line_parts[1] = new_material_name
                        new_line = line_parts[0] + '"' + line_parts[1] + '"' + line_parts[2]
                        script.append(new_line)
                    else:
                        script.append(line)
                else:
                    script.append(line)
        
        return script
    
#============================================================================================================================================
#============================================================================================================================================
#============================================================================================================================================

class SURFACES_ATTRIBUTE():
    instances = {}
    
    def __init__(self, index, name):
        self.index = index
        self.name = name
        self.surface = None
        SURFACES_ATTRIBUTE.instances[int(index)] = self


    @classmethod
    def load_files(cls, path):
        for file in os.scandir(path):
            if file.name.endswith(".xml"): # filtre les fichiers, et évite les surfaces de séparation
                xml_file = ET.parse(file)
                xml_data = xml_file.getroot()
                
                surface_attribute_instance = cls(int(xml_data.get("Index")) , xml_data.get("Name").replace("Material - ", "")) # créé l'instance de class de la surface
                for section in xml_data:
                    setattr(surface_attribute_instance, section.tag, section) # rempli l'instance avec les attributs du xml
                
                
                surface_attribute_instance.find_surface()
                
                
    def find_surface(self):
        '''trouve la SURFACE associée à partir du nom, afin de lier le script_1D à travers l'index'''
        if surface_instance := SURFACES.instances.get(self.name):
            surface_instance.surface_attribute = self
            self.surface = surface_instance
            
        else:
            print("<WARNING> unassociated material:", self.index, self.name, "because the '/' is not allowed. Please avoid it in names.")

#============================================================================================================================================
#============================================================================================================================================
#============================================================================================================================================

class OBJET(): 
    unknown_materials = [] # Les matériaux non trouvés sont mis ici
    instances = {}

    def __init__(self,xml_data, mainguid, name, relative_path):
        self.xml_data = xml_data
        self.mainguid = mainguid
        self.name = name
        self.relative_path = relative_path
        self.textures = {} #  {texture_name : texture file}
        self.texture_folder = None
        self.preview = None
        self.sections_list = []
        OBJET.instances[mainguid] = self
            

    @classmethod
    def load_files(cls, path, original_path):
        global debug_i
        for file in os.scandir(path):
            if file.is_dir():
                OBJET.load_files(file.path, original_path)
            
            elif file.name.endswith(".xml"):
                
                # Retrouve le chemin relatif par rapport à la racine du dossier pour conserver la hiérarchie.
                relative_path = os.path.relpath(path, original_path)
                # extrait les données du fichier
                xml_file = ET.parse(file)
                xml_data = xml_file.getroot()
            
                mainguid = xml_data.get("MainGUID")
                    
                objet_instance = OBJET(xml_data, mainguid, file.name.replace(".xml", ""), relative_path)
                for section in xml_data:
                    # Si il ya déjà une section de ce nom, créé une liste à la place.
                    if hasattr(objet_instance, section.tag):
                        if type(getattr(object_instance, section.tag)) is not list:
                            setattr(objet_instance, section.tag, [getattr(object_instance, section.tag)])
                            object_instance.section_list.append(section.tag)
                            
                        exec(f"objet_instance.{section.tag}.append(section)")
                            
                    else:
                        setattr(objet_instance, section.tag, section)
                
                objet_instance.find_textures()

            
    def print(self):
        print(self.name)
        for attr in dir(self):
            if not callable(getattr(self, attr)) and not "__" in attr:
                print("    " + attr) #, type(getattr(self, attr)))

    def find_textures(self):
        '''Trouve toutes les textures intégrées à l'objet, et les répertorie dans les attribut de l'instance'''
        # lis la section picture
        if hasattr(self, "Picture"):
        # récupere le path de la preview
            self.preview = self.Picture.get("path")
        
        
        if hasattr(self, "GDLPict"):
            # Assure de toujours avoir le meme format.
            GDLPict_list = []
            if type(self.GDLPict) is list:
                GDLPict_list = self.GDLPict
            else:
                GDLPict_list = [self.GDLPict]
                

            # trouve la texture
            for GDLPict in GDLPict_list:
                path = GDLPict.get("path")
            
        
            # trouve le dossier texture à partir de ça
            # sauvegarde la texture, et le dossier dans les attributs de l'instance
            self.textures[GDLPict.get("SubIndent")] = xml_folder + GDLPict.get("path").replace("/", os.sep)
            self.texture_folder = os.path.dirname(xml_folder + GDLPict.get("path").replace("/", os.sep))

        
    def merge_materials(self):
        '''Trouve toutes les surfaces référencées dans les paramètres de l'objet, et les répertorie dans les attributs de la classe.
        Dans un second temps, cherche la surface correspondante dans la class SURFACE pour demander intégration.'''

        
        script_1d_materials = []
        
        param = self.ParamSection.find("Parameters")
        for material in param.findall("Material"):
            material_name = material.get("Name")
            material_index = material.find("Value").text
    
            # Récupère le script 1d de la surface à laquelle le matériau est lié
            if surface_attribute := SURFACES_ATTRIBUTE.instances.get(int(material_index)):
                if surface_instance := surface_attribute.surface:
                    script_1d_materials += surface_instance.get_script_1d(material_name) # La fonction remplace le nom si un autre nom lui est donné.
                    # Renome l'ancien paramètre pour le moment afin qu'il ne gène pas. Il n'a plus aucun effet, mais on le garde pour plus tard.
                    material.set("Name", "_old_" + material_name)
                    
                    for texture_name, texture in surface_instance.textures.items():
                        self.add_gdlpict(texture)
                else:
                    print(f"<WARNING> Surface introuvable pour le surface_attribute {surface_attribute.name}")

            else:
                if not material_index in OBJET.unknown_materials:
                    OBJET.unknown_materials.append(material_index)
                print(f"<WARNING> Matériau {material_name} avec index {material_index} non trouvé dans l'objet {self.name}")
                
        
        # récupère le Script_1D de l'objet
        script_1d_objet = self.get_script_1d()
        
        # Ajoute une ligne pour afficher la représentation 2D de l'objet sinon il ne l'affiche pas.
        if not "FRAGMENT2 ALL, 0" in script_1d_objet and len(script_1d_materials):
            script_1d_materials += "FRAGMENT2 ALL, 0"
            
        # Recompile les scripts en un string.
        self.set_script_1d(script_1d_objet + script_1d_materials)
        
        
        
        
        
            
    def get_script_1d(self):
        if not hasattr(self, "Script_1D"):
            data = '''<Script_1D SectVersion="20" SectionFlags="0" SubIdent="0">
<![CDATA[]]>
</Script_1D>'''  
            self.Script_1D = ET.fromstring(data)
            print(f"Script_1D manquant dans objet {self.name}")
        script = []
        lines = self.Script_1D.text.split("\n")
        for line in lines:
            if line.startswith("<![CDATA["):
                script.append(line.replace("<![CDATA[", ""))
            elif line.endswith("]]>"):
                script.append(line.replace("]]>", ""))
            else:
                script.append(line)
        
        return script

    def set_script_1d(self, script):
        script_str = "<![CDATA[\n"
        for line in script:
            script_str += line + "\n"
        script_str += "]]>\n"


    def add_gdlpict(self, texture):
        ext = texture.name.split(".")[-1]
        if not hasattr(self, "GDLPict"):
            setattr(self, "GDLPict", [])
        data = f'''<GDLPict MIME="image/{ext}" SectVersion="19" SectionFlags="0" SubIdent="{len(self.GDLPict)}" path="{texture.path}"/>'''
        self.GDLPict.append(ET.fromstring(data))
        
    def compile_xml(self):
        attributes = [attr for attr in dir(self) if attr in self.sections_list + ["GDLPict", "Script_1D"]]
        for attr in attributes:
            print(str(type(getattr(self, attr))), attr)
            if "xml.etree.ElementTree.Element" in str(type(getattr(self, attr))):
                self.xml_data.set(attr, getattr(self, attr))
            elif type(getattr(self, attr)) is list:
                for element in getattr(self, attr):
                    self.xml_data.set(element.tag, element)
        
        output_path = 'C:\\Users\\clovis.flayols\\Desktop\\Object surface converter\\objects XML converted\\' + self.relative_path + "\\"
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        file_path = output_path + self.name + ".xml"
        new_tree = ET.ElementTree(self.xml_data)
        new_tree.write(file_path, encoding="utf-8", xml_declaration=True)
                
                
                
# ================================================================================================================
# ================================================================================================================
# ================================================================================================================
# ================================================================================================================
# ================================================================================================================
# ================================================================================================================
# ================================================================================================================
# ================================================================================================================
    
# Charge les surfaces
SURFACES.load_files(xml_folder)
# Charge les attributs de surface
SURFACES_ATTRIBUTE.load_files(xml_attribute_folder)
# Charge les objets
OBJET.load_files(objet_xml_folder, objet_xml_folder)


# Combine les surfaces dans l'objet.
for objet in OBJET.instances.values():
    objet.merge_materials()
    objet.compile_xml()
    

# cleanup
SURFACES.instances = {}
cached_texture_folder = {}
OBJET.instances = {}
