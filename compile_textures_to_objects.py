import xml.etree.ElementTree as ET
import xml.sax.saxutils as su
import os
import shutil
import re


xml_folder = 'E:\\Work\\Pro\\Christian FLOUR\\Bibliotheque Archicad\\Object surface converter\\surfaces XML'
xml_attribute_folder = 'E:\\Work\\Pro\\Christian FLOUR\\Bibliotheque Archicad\\Object surface converter\\surfaces XML attribute'
gsm_texture_folder = 'E:\\Work\\Pro\\Christian FLOUR\\Bibliotheque Archicad\\Object surface converter\\surfaces GSM\\[TImg] Textures'
cached_texture_folder = {}
objet_xml_folder = 'E:\\Work\\Pro\\Christian FLOUR\\Bibliotheque Archicad\\Object surface converter\\objets XML'
output_folder = 'C:\\Users\\Asloric\\Desktop\\tests\\objets XML\\'
warning_level = 3 # 0 = info, 1 = warning, 2 = error, 3=silence.

#============================================================================================================================================
#============================================================================================================================================
#============================================================================================================================================

# Cette partie permet de remplacer le serialiseur xml afin de conserver le "CDATA" dans la sortie.

def CDATA(text=None):
    element = ET.Element('![CDATA[')
    element.text = text
    return element

ET._original_serialize_xml = ET._serialize_xml

def _serialize_xml(write, elem, qnames, namespaces,short_empty_elements, **kwargs):
    if elem.text is not None:
        next_indent_level = elem.text.count("\t")
    else:
        next_indent_level = 0

    if elem.tag == '![CDATA[':
        write("<{}{}]]>".format(elem.tag, elem.text))
        if elem.tail:
            write(ET._escape_cdata(elem.tail))
        else:
            current_indent_level = kwargs.get("current_indent_level")
            elem.tail = '\t' * (current_indent_level if current_indent_level else 0)
            write(ET._escape_cdata(elem.tail))
    else:
        return ET._original_serialize_xml(write, elem, qnames, namespaces,short_empty_elements, current_indent_level=next_indent_level, **kwargs)

ET._serialize_xml = ET._serialize['xml'] = _serialize_xml

def cleanString(incomingString):
    newstring = incomingString
    newstring = newstring.replace("!","")
    newstring = newstring.replace("@","")
    newstring = newstring.replace("#","")
    newstring = newstring.replace("$","")
    newstring = newstring.replace("%","")
    newstring = newstring.replace("^","")
    newstring = newstring.replace("&","and")
    newstring = newstring.replace("*","")
    newstring = newstring.replace("(","")
    newstring = newstring.replace(")","")
    newstring = newstring.replace("+","")
    newstring = newstring.replace("=","")
    newstring = newstring.replace("?","")
    newstring = newstring.replace("\'","")
    newstring = newstring.replace("\"","")
    newstring = newstring.replace("{","")
    newstring = newstring.replace("}","")
    newstring = newstring.replace("[","")
    newstring = newstring.replace("]","")
    newstring = newstring.replace("<","")
    newstring = newstring.replace(">","")
    newstring = newstring.replace("~","")
    newstring = newstring.replace("`","")
    newstring = newstring.replace(":","")
    newstring = newstring.replace(";","")
    newstring = newstring.replace("|","")
    newstring = newstring.replace("\\","")
    newstring = newstring.replace("/","")        
    newstring = newstring.replace(".","")        
    newstring = newstring.replace(" ","_")        
    newstring = newstring.replace("é","e")        
    newstring = newstring.replace("è","e")        
    newstring = newstring.replace("à","a")        
    if len(newstring) > 28:
        return newstring[0:28] # max archicad lenght is 36. minus the ovr_sf_{mat_name}*
    return newstring
    

#============================================================================================================================================
#============================================================================================================================================
#============================================================================================================================================


class METACLASS():

    def debug(self, text, level=0):
        global warning_level
        info_level = ["<INFO>", "<WARNING>", "<ERROR>"]
        if level >= warning_level:
            infos = ''.join(str(t) for t in text)
            print(info_level[level], infos)

#============================================================================================================================================
#============================================================================================================================================
#============================================================================================================================================


class SURFACES(METACLASS):
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
                

    def find_textures(self):
        #if hasattr(self, "Picture"):  # Pas utile pour la compilation des textures dans les objets.
        # récupere le path de la preview
            #self.prefiew = self.Picture.get("path")
            
        # Lis le script_1D et cherche les lignes file_dependance.
        script_1d = self.Script_1D.text.split("\n") # Créé une liste 
        for line in script_1d:
            if line.startswith("file_dependence") or "define texture" in line:
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

    
    def get_script_1d(self, material_name=None, new_material_index=None, custom_script=None, is_texture=False, is_material=False):
        script = []
        found_texture_names = []
        if custom_script is not None:
            lines = custom_script
        else:
            lines = self.Script_1D.text.split("\n")
        for line in lines:
            if line.startswith("call "):
                pass
            else:
                if material_name and new_material_index and material_name in line:
                    line_lower = line.lower()
                    if line_lower.startswith("file_dependence"):
                        pass
                    else:
                        if is_texture and "define texture" in line_lower:
                            
                            line_parts = line.rsplit(material_name, 1)
                        else:
                            if is_texture and "ind(texture" in line_lower:
                                script.append(line)
                                continue
                            else:
                                if is_material and not "define material" in line_lower:
                                    script.append(line)
                                    continue
                                else:
                                    line_parts = line.split(material_name, 1)

                        separator = '"' if type(new_material_index) is str else ""
                        new_line = line_parts[0][:-1] + separator  + str(new_material_index)  + separator + line_parts[1][1:]
                        script.append(new_line)


                else:
                    script.append(line)

        return script
    
#============================================================================================================================================
#============================================================================================================================================
#============================================================================================================================================

class SURFACES_ATTRIBUTE(METACLASS):
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
            super().debug(("unassociated material:", self.index, self.name, "because the '/' is not allowed. Please avoid it in names."), 0)

#============================================================================================================================================
#============================================================================================================================================
#============================================================================================================================================

class OBJET(METACLASS): 
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
        self.cdata_sections_list = []
        OBJET.instances[mainguid] = self
            

    @classmethod
    def load_files(cls, path, original_path):
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
                        if type(getattr(objet_instance, section.tag)) is not list:
                            setattr(objet_instance, section.tag, [getattr(objet_instance, section.tag)])
                            
                            
                        exec(f"objet_instance.{section.tag}.append(section)")
                            
                    else:
                        setattr(objet_instance, section.tag, section)


                    if section.text not in ["\n\t", None]:
                        if section.text == "\n\n":
                            section.text = ""
                        objet_instance.cdata_sections_list.append(section.tag)
                    objet_instance.sections_list.append(section.tag)

                objet_instance.find_textures()

    def find_textures(self):
        '''Trouve toutes les textures intégrées à l'objet, et les répertorie dans les attribut de l'instance'''
        # lis la section picture
        if hasattr(self, "Picture"):
        # récupere le path de la preview
            self.preview = self.Picture.get("path")

            if self.preview:
                # Copie la texture dans le bon dossier.
                original_texture_path = objet_xml_folder + os.sep + self.preview
                path = output_folder + self.relative_path + os.sep + self.name + os.sep

                # créé le dossier si nécessaire
                if not os.path.exists(path):
                    os.makedirs(path)

                shutil.copy2(original_texture_path, path)
                
        
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
            parameter_material_name = material.get("Name")
            material_index = material.find("Value").text
    
            # Récupère le script 1d de la surface à laquelle le matériau est lié
            if surface_attribute := SURFACES_ATTRIBUTE.instances.get(int(material_index)):
                if surface_instance := surface_attribute.surface:
                    # Renome l'ancien paramètre pour le moment afin qu'il ne gène pas. Il n'a plus aucun effet, mais on le garde pour plus tard.
                    material.set("Name", "_old_" + parameter_material_name)
                    curent_script = surface_instance.get_script_1d(surface_instance.name, parameter_material_name, is_texture=False, is_material=True)

                    curent_script.append(f'{parameter_material_name} = IND(MATERIAL, "{parameter_material_name}")')

                    curent_script = surface_instance.get_script_1d("Texture1", "texture_" + surface_instance.name, custom_script=curent_script, is_texture=False, is_material=False)

                    for texture_name, texture in surface_instance.textures.items():
                        image_index = self.add_gdlpict(texture)
                        if image_index:
                            curent_script = surface_instance.get_script_1d(texture_name, image_index, custom_script=curent_script if len(curent_script) > 0 else None, is_texture=True, is_material=False) # La fonction remplace le nom si un autre nom lui est donné.

                    script_1d_materials += curent_script

                else:
                    super().debug((f"Surface introuvable pour le surface_attribute {surface_attribute.name}"), 1)

            else:
                if not material_index in OBJET.unknown_materials:
                    OBJET.unknown_materials.append(material_index)
                super().debug((f"Matériau {parameter_material_name} avec index {material_index} non trouvé dans l'objet {self.name}"), 2)
                
        
        # récupère le Script_1D de l'objet
        script_1d_objet = self.get_script_1d()
        
        # Ajoute une ligne pour afficher la représentation 2D de l'objet sinon il ne l'affiche pas.
        if not "FRAGMENT2 ALL, 0" in script_1d_objet and len(script_1d_materials):
            script_1d_materials += ["FRAGMENT2 ALL, 0"]
        
        # Recompile les scripts en un string.
        self.Script_1D.text =  (script_1d_objet.text if script_1d_objet.text else "")+"\n".join(script_1d_materials if script_1d_materials else "")

    def get_script_1d(self):
        if not hasattr(self, "Script_1D"):
            data = '''<Script_1D SectVersion="20" SectionFlags="0" SubIdent="0"><![CDATA[]]></Script_1D>'''  
            self.Script_1D = ET.fromstring(data)
            super().debug((f"Script_1D manquant dans objet {self.name}"), 0)
        return self.Script_1D
            

    def add_gdlpict(self, texture):
        ext = texture.name.split(".")[-1]
        if not hasattr(self, "GDLPict"):
            setattr(self, "GDLPict", [])
        image_index = len(self.GDLPict)+1
        texture_path = str(self.relative_path + "/" + self.name + "/" + texture.name).replace("\\", '/')
        data = f'''<GDLPict MIME="image/{ext}" SectVersion="19" SectionFlags="0" SubIdent="{image_index}" path="{texture_path}"/>'''
        try:
            section = ET.fromstring(data)
            self.GDLPict.append(section)
        except:
            super().debug(f"could not create texture {texture.name} for object {self.name}. probably due to name issue.", 2)

        # Copie la texture dans le bon dossier.
        original_texture_path = texture.path
        path = output_folder + self.relative_path + os.sep + self.name + os.sep

        # créé le dossier si nécessaire
        if not os.path.exists(path):
            os.makedirs(path)

        shutil.copy2(original_texture_path, path)

        return image_index

    @staticmethod
    def check_CDATA(section):
        '''Vérifie que toutes les sections qui doivent avoir du CDATA en aient.'''
        # une section CDATA
        # if section.text in ["\n\n"]:
        x = 1
        if section.tag in ["MName", "Description", "Script_3D", "Script_2D", "Script_1D", "Script_PR", "Script_UI", "Script_VL", "Script_FWM", "Script_BWM", "Keywords", "Comment"]:
            Ctext = CDATA(section.text)
            section.text = None
            section.append(Ctext)
            return section

        else:
            subsection_list = [subsection for subsection in section]
            for subsection in section:
                new_section = OBJET.check_CDATA(subsection)
                section.insert(subsection_list.index(subsection), new_section)
                section.remove(subsection)
            return section



    def compile_xml(self):
        attributes = [attr for attr in dir(self) if attr in self.sections_list + ["GDLPict", "Script_1D"]]                
                
        # Créer un nouveau xml
        tree = ET.ElementTree()

        # Créer un nouvel élément racine pour le xml
        root = ET.Element("Symbol")
        for attrib, value in self.xml_data.attrib.items():
            root.attrib[attrib] = value

        # Ajouter les sections au xml
        for attr in attributes:
            # Si la section est une liste, ajouter chaque élément de la liste à l'arbre
            if isinstance(getattr(self, attr), list):
                for item in getattr(self, attr):
                    root.append(OBJET.check_CDATA(item))
            # Sinon, ajouter directement la section à l'arbre
            else:
                section = getattr(self, attr)
                root.append(OBJET.check_CDATA(section))

        # Ajouter l'élément racine à l'arbre
        tree._setroot(root)

        global output_folder
        output_path = output_folder + self.relative_path + "\\"
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        file_path = output_path + self.name + ".xml"

        # Enregistrer l'arbre dans un fichier XML
        tree.write(file_path, encoding="utf-8", xml_declaration=True)
        

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

# objet = list(OBJET.instances.values())[1]
# objet.merge_materials()
# objet.compile_xml()


# cleanup
SURFACES.instances = {}
cached_texture_folder = {}
OBJET.instances = {}
