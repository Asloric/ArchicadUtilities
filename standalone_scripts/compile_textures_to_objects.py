# compile_textures_to_objects.py - Standalone Archicad library batch processor.
# NOT part of the Blender addon. Run directly as a Python script.
#
# Purpose: Embed surface (material) definitions and their associated textures
# into Archicad object XML files so each object is self-contained.
#
# Why this is needed:
#   When Archicad exports objects to XML, material parameters are stored as
#   integer index references (e.g. Material index=42). These indices are
#   library-specific and break if the object is imported into a project
#   with a different surface library. This script embeds the full surface
#   GDL script (DEFINE MATERIAL / DEFINE TEXTURE) directly into the object's
#   Script_1D, making the object portable and self-contained.
#
# Input folder structure expected (all paths relative to script working dir):
#   \surfaces XML\          - one .xml per Archicad surface (exported from AC)
#   \surfaces XML attribute\- one .xml per Archicad surface attribute (contains index)
#   \surfaces GSM\[TImg] Textures\ - texture image files used by surfaces
#   \objets XML\            - object .xml files to process (may be nested)
#
# Output:
#   \objets XML Converted\  - processed .xml files with embedded surfaces/textures
#                             (subdirectory tree mirrored from input)
#
# Key technique - CDATA preservation:
#   Python's xml.etree.ElementTree strips CDATA sections on parse, converting
#   them to plain text. Archicad XML requires explicit <![CDATA[...]]> wrappers
#   around GDL script sections. This script monkey-patches ET._serialize_xml
#   to re-emit CDATA wrappers for GDL script fields on write.
#
# Processing pipeline:
#   1. SURFACES.load_files()          - parse surface XMLs into SURFACES instances
#   2. SURFACES_ATTRIBUTE.load_files()- parse surface attribute XMLs, link to SURFACES by name
#   3. OBJET.load_files()             - parse object XMLs recursively
#   4. objet.merge_materials()        - for each object, find referenced surfaces,
#                                       embed their Script_1D + textures, add override GDL
#   5. objet.compile_xml()            - write processed XML to output folder

import xml.etree.ElementTree as ET
import xml.sax.saxutils as su
import os
import shutil
import re


# Input/output folder paths (relative to CWD). Change before use.
xml_folder = '\\surfaces XML'
xml_attribute_folder = '\\surfaces XML attribute'
gsm_texture_folder = '\\surfaces GSM\\[TImg] Textures'
cached_texture_folder = {}  # Lazy-populated cache: {filename_without_ext: DirEntry}
objet_xml_folder = '\\objets XML'
output_folder = '\\objets XML Converted\\'
warning_level = 3 # 0 = info, 1 = warning, 2 = error, 3=silence.

#============================================================================================================================================
#============================================================================================================================================
#============================================================================================================================================

# CDATA preservation patch for xml.etree.ElementTree.
# ET strips CDATA on parse and does not re-emit it on write. Archicad XML requires
# CDATA wrappers around all GDL script sections. We work around this by:
#   1. Creating a fake XML element with tag '![CDATA[' to act as a CDATA sentinel node.
#   2. Monkey-patching ET._serialize_xml so that when it encounters the sentinel tag,
#      it emits a literal <![CDATA[...]]> block instead of a normal XML element.

def CDATA(text=None):
    """Create a CDATA sentinel element. Tag '![CDATA[' is not valid XML but is
    detected by the patched serializer to emit a raw CDATA block."""
    element = ET.Element('![CDATA[')
    element.text = text
    return element

ET._original_serialize_xml = ET._serialize_xml

def _serialize_xml(write, elem, qnames, namespaces,short_empty_elements, **kwargs):
    # Count leading tabs to track indent depth for tail whitespace restoration.
    if elem.text is not None:
        next_indent_level = elem.text.count("\t")
    else:
        next_indent_level = 0

    if elem.tag == '![CDATA[':
        # Emit the raw CDATA block instead of an XML element.
        write("<{}{}]]>".format(elem.tag, elem.text))
        if elem.tail:
            write(ET._escape_cdata(elem.tail))
        else:
            # Restore indentation whitespace after closing ]]>.
            current_indent_level = kwargs.get("current_indent_level")
            elem.tail = '\t' * (current_indent_level if current_indent_level else 0)
            write(ET._escape_cdata(elem.tail))
    else:
        return ET._original_serialize_xml(write, elem, qnames, namespaces,short_empty_elements, current_indent_level=next_indent_level, **kwargs)

# Replace both the function reference and the format-dispatch dict entry.
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
    """Shared base for SURFACES, SURFACES_ATTRIBUTE, OBJET.
    Provides a debug() helper that gates output by global warning_level."""

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
    """Represents one Archicad surface (material) exported to XML.

    Each instance corresponds to one .xml file from \surfaces XML\.
    XML sections are stored as attributes (e.g. self.Script_1D, self.Picture).
    self.textures maps texture filenames to their DirEntry objects.
    self.surface_attribute is linked by SURFACES_ATTRIBUTE.find_surface() after loading.
    """
    instances = {}  # {surface_name: SURFACES instance}

    def __init__(self, name):
        self.name = name
        self.textures = {} #  {texture_name : texture file DirEntry}
        self.preview = None
        self.surface_attribute = None  # Linked SURFACES_ATTRIBUTE; set by find_surface()
        SURFACES.instances[name] = self

    @classmethod
    def load_files(cls, path):
        """Parse all .xml surface files in path. Non-.xml files (separator lines etc.) are skipped."""
        for file in os.scandir(path):
            if file.name.endswith(".xml"):
                xml_file = ET.parse(file)
                xml_data = xml_file.getroot()

                surface_instance = cls(file.name.replace(".xml", ""))
                # Dynamically attach each XML child section as an attribute.
                for section in xml_data:
                    setattr(surface_instance, section.tag, section)

                surface_instance.find_textures()


    def find_textures(self):
        """Scan Script_1D for file_dependence and define texture lines to collect texture filenames.

        Texture names are extracted by splitting on the backtick character (`).
        NOTE: The ` character in Archicad XML is NOT a regular backtick (ASCII 96) but the
        typographic backtick from AltGr+7. If texture names are not found, check encoding.
        Texture DirEntry objects are cached in cached_texture_folder on first call.
        """
        script_1d = self.Script_1D.text.split("\n")
        for line in script_1d:
            if line.startswith("file_dependence") or "define texture" in line:
                texture_file_name = line.split("`")[1]  # Extract name between backtick delimiters

                # Lazy-populate the global texture cache on first texture lookup.
                if not len(cached_texture_folder.keys()):
                    for file in os.scandir(gsm_texture_folder):
                        cached_texture_folder[file.name.split(".")[0]] = file

                if texture_file := cached_texture_folder.get(texture_file_name):
                    self.textures[texture_file_name] = texture_file


    def get_script_1d(self, material_name=None, new_material_index=None, custom_script=None, is_texture=False, is_material=False):
        """Return Script_1D lines with material/texture name references replaced.

        Parameters:
          material_name       - name to find and replace in script lines
          new_material_index  - replacement value (int for GDLPict index, str for named reference)
          custom_script       - if given, use this list of lines instead of self.Script_1D
          is_texture          - if True, operate on DEFINE TEXTURE lines (use rsplit to replace last occurrence)
          is_material         - if True, skip lines that are not DEFINE MATERIAL lines

        Replacement rules:
          - Lines starting with "call" are dropped (sub-object calls not needed in embedded script)
          - file_dependence lines are dropped (textures will be embedded as GDLPict instead)
          - For "define texture" lines: rsplit on material_name (replace rightmost occurrence)
          - For "ind(texture" lines when is_texture: pass through unchanged (index already correct)
          - For non-DEFINE MATERIAL lines when is_material: pass through unchanged
          - Otherwise: split on material_name and substitute new_material_index
          - Separator: '"' if new_material_index is a string (named ref), '' if it's an int (index)
        """
        script = []
        found_texture_names = []
        if custom_script is not None:
            lines = custom_script
        else:
            lines = self.Script_1D.text.split("\n")
        for line in lines:
            if line.startswith("call "):
                pass  # Drop sub-object call lines
            else:
                if material_name and new_material_index and material_name in line:
                    line_lower = line.lower()
                    if line_lower.startswith("file_dependence"):
                        pass  # Drop file_dependence lines (textures embedded as GDLPict)
                    else:
                        if is_texture and "define texture" in line_lower:
                            # Replace rightmost occurrence (texture name is at the end of the line).
                            line_parts = line.rsplit(material_name, 1)
                        else:
                            if is_texture and "ind(texture" in line_lower:
                                # IND(TEXTURE,...) reference - pass through, index substituted elsewhere.
                                script.append(line)
                                continue
                            else:
                                if is_material and not "define material" in line_lower:
                                    # Non-DEFINE MATERIAL line in material pass - pass through.
                                    script.append(line)
                                    continue
                                else:
                                    line_parts = line.split(material_name, 1)

                        # Wrap in quotes if replacement is a string (named reference), bare if int (index).
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
    """Represents one Archicad surface attribute record (the index mapping for a surface).

    Archicad stores surface attributes in a separate XML export that maps integer indices
    to surface names. This class links those indices to SURFACES instances by name.
    Keyed by integer index so OBJET.merge_materials() can look up by material parameter value.
    """
    instances = {}  # {int index: SURFACES_ATTRIBUTE instance}

    def __init__(self, index, name):
        self.index = index
        self.name = name
        self.surface = None  # Linked SURFACES instance; set by find_surface()
        SURFACES_ATTRIBUTE.instances[int(index)] = self

    @classmethod
    def load_files(cls, path):
        """Parse all .xml surface attribute files. The "Material - " prefix is stripped from names
        to match the surface names stored in SURFACES.instances."""
        for file in os.scandir(path):
            if file.name.endswith(".xml"):
                xml_file = ET.parse(file)
                xml_data = xml_file.getroot()

                # Index is the Archicad internal material index used in object parameter values.
                # Name has "Material - " prefix stripped so it matches SURFACES.instances keys.
                surface_attribute_instance = cls(int(xml_data.get("Index")), xml_data.get("Name").replace("Material - ", ""))
                for section in xml_data:
                    setattr(surface_attribute_instance, section.tag, section)

                surface_attribute_instance.find_surface()


    def find_surface(self):
        """Link this attribute to a SURFACES instance by name.

        If no match is found, the surface name may contain '/' which is stripped by Archicad
        export or the naming convention differs between the two XML exports.
        """
        if surface_instance := SURFACES.instances.get(self.name):
            surface_instance.surface_attribute = self
            self.surface = surface_instance
        else:
            super().debug(("unassociated material:", self.index, self.name, "because the '/' is not allowed. Please avoid it in names."), 0)

#============================================================================================================================================
#============================================================================================================================================
#============================================================================================================================================

class OBJET(METACLASS):
    """Represents one Archicad object XML file to be processed.

    Each instance holds the parsed XML tree, tracks all XML sections as attributes
    (similar to SURFACES), and maintains lists of sections that contain CDATA content.
    Duplicate section tags (e.g. multiple GDLPict entries) are stored as lists.

    Processing flow per instance:
      find_textures()   - copy preview image; index any embedded GDLPict textures
      merge_materials() - embed surface scripts and textures, add override GDL
      compile_xml()     - write the modified XML to the output folder
    """
    unknown_materials = []  # Class-level list of unresolved material indices (logged once each)
    instances = {}  # {MainGUID string: OBJET instance}

    def __init__(self, xml_data, mainguid, name, relative_path):
        self.xml_data = xml_data
        self.mainguid = mainguid
        self.name = name
        self.relative_path = relative_path
        self.textures = {}  # {texture_name: texture file DirEntry}
        self.texture_folder = None
        self.preview = None
        self.sections_list = []       # Ordered list of all XML section tag names
        self.cdata_sections_list = [] # Subset of sections_list that had non-empty text (need CDATA on write)
        OBJET.instances[mainguid] = self


    @classmethod
    def load_files(cls, path, original_path):
        """Recursively load all .xml object files from path.
        original_path is the root folder, used to compute relative paths for output mirroring.
        Duplicate XML section tags are accumulated into lists via exec() (avoids setattr collision).
        """
        for file in os.scandir(path):
            if file.is_dir():
                OBJET.load_files(file.path, original_path)

            elif file.name.endswith(".xml"):

                # Preserve subfolder hierarchy in output by computing path relative to root.
                relative_path = os.path.relpath(path, original_path)
                xml_file = ET.parse(file)
                xml_data = xml_file.getroot()

                mainguid = xml_data.get("MainGUID")

                objet_instance = OBJET(xml_data, mainguid, file.name.replace(".xml", ""), relative_path)
                for section in xml_data:
                    # If a section tag already exists (e.g. multiple GDLPict), convert to list.
                    if hasattr(objet_instance, section.tag):
                        if type(getattr(objet_instance, section.tag)) is not list:
                            setattr(objet_instance, section.tag, [getattr(objet_instance, section.tag)])
                        # NOTE: exec() used here because setattr can't .append to a list attribute.
                        exec(f"objet_instance.{section.tag}.append(section)")
                    else:
                        setattr(objet_instance, section.tag, section)

                    # Track which sections have non-trivial text (will need CDATA wrapping on output).
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
        """Embed surface scripts and textures into this object, replacing index references.

        For each Material parameter in the object's ParamSection:
          1. Look up the material index in SURFACES_ATTRIBUTE.instances to find the surface.
          2. Rename the original parameter to "_old_<name>" (kept for override detection).
          3. Build a GDL override block in Script_3D:
               IF _old_<name> = 0 OR _old_<name> = <original_index> THEN
                   <name> = IND(MATERIAL, "<name>")   ! Use embedded surface
               ELSE
                   <name> = _old_<name>               ! Use user-overridden index
               ENDIF
             NOTE: This is in Script_3D because Script_1D only runs on library load,
             not on each 3D regeneration.
          4. Get the surface's Script_1D lines (DEFINE MATERIAL / DEFINE TEXTURE).
          5. Replace texture file references with GDLPict integer indices (embedded images).
          6. Accumulate all surface scripts into script_1d_materials.
        Finally, prepend all surface scripts to the object's Script_1D.
        A FRAGMENT2 ALL, 0 line is appended if not already present (required for 2D display).
        """
        script_1d_materials = []

        param = self.ParamSection.find("Parameters")
        choose_material_script = ""
        for material in param.findall("Material"):
            parameter_material_name = material.get("Name")
            material_index = material.find("Value").text

            if surface_attribute := SURFACES_ATTRIBUTE.instances.get(int(material_index)):
                if surface_instance := surface_attribute.surface:
                    # Rename parameter so the embedded surface is used by default.
                    # The old index is preserved under "_old_<name>" for user override detection.
                    material.set("Name", "_old_" + parameter_material_name)

                    # Get the DEFINE MATERIAL lines from the surface script.
                    curent_script = surface_instance.get_script_1d(surface_instance.name, parameter_material_name, is_texture=False, is_material=True)

                    # Build the GDL override block added to Script_3D.
                    choose_material_script += f'''
IF _old_{parameter_material_name} = 0 OR _old_{parameter_material_name} = {str(material_index)} THEN
    {parameter_material_name} = IND(MATERIAL, "{parameter_material_name}")
ELSE
    {parameter_material_name} = _old_{parameter_material_name}
ENDIF
'''
                    # Replace "Texture1" references with the surface-specific texture parameter name.
                    curent_script = surface_instance.get_script_1d("Texture1", "texture_" + surface_instance.name, custom_script=curent_script, is_texture=False, is_material=False)

                    # For each texture file, embed it as a GDLPict entry and replace the filename
                    # reference in the script with the new integer GDLPict index.
                    for texture_name, texture in surface_instance.textures.items():
                        image_index = self.add_gdlpict(texture)
                        if image_index:
                            curent_script = surface_instance.get_script_1d(texture_name, image_index, custom_script=curent_script if len(curent_script) > 0 else None, is_texture=True, is_material=False)

                    script_1d_materials += curent_script

                else:
                    super().debug((f"Surface introuvable pour le surface_attribute {surface_attribute.name}"), 1)

            else:
                if not material_index in OBJET.unknown_materials:
                    OBJET.unknown_materials.append(material_index)
                super().debug((f"Matériau {parameter_material_name} avec index {material_index} non trouvé dans l'objet {self.name}"), 2)

        # Prepend the material override GDL block to Script_3D.
        self.Script_3D.text = choose_material_script + self.Script_3D.text

        script_1d_objet = self.get_script_1d()

        # FRAGMENT2 ALL, 0 is required for Archicad to display the 2D symbol when a 1D script is present.
        if not "FRAGMENT2 ALL, 0" in script_1d_objet and len(script_1d_materials):
            script_1d_materials += ["FRAGMENT2 ALL, 0"]

        # Combine original Script_1D with all embedded surface scripts.
        self.Script_1D.text = (script_1d_objet.text if script_1d_objet.text else "") + "\n".join(script_1d_materials if script_1d_materials else "")

    def get_script_1d(self):
        if not hasattr(self, "Script_1D"):
            data = '''<Script_1D SectVersion="20" SectionFlags="0" SubIdent="0"><![CDATA[]]></Script_1D>'''  
            self.Script_1D = ET.fromstring(data)
            super().debug((f"Script_1D manquant dans objet {self.name}"), 0)
        return self.Script_1D
            

    def add_gdlpict(self, texture):
        """Embed a texture file as a GDLPict XML section and copy it to the output folder.

        GDLPict is Archicad's mechanism for embedding binary image data references in object XML.
        SubIdent is the 1-based integer index used in GDL DEFINE TEXTURE ... IND(GDLPICT, n) calls.
        The path attribute is relative, matching the output subfolder structure.

        Returns the new image_index (int) so the caller can substitute it into script lines.
        Returns None implicitly if ET.fromstring() fails (XML element not appended in that case).
        """
        ext = texture.name.split(".")[-1]
        if not hasattr(self, "GDLPict"):
            setattr(self, "GDLPict", [])
        # SubIdent is 1-based; next index = current list length + 1.
        image_index = len(self.GDLPict) + 1
        texture_path = str(self.relative_path + "/" + self.name + "/" + texture.name).replace("\\", '/')
        data = f'''<GDLPict MIME="image/{ext}" SectVersion="19" SectionFlags="0" SubIdent="{image_index}" path="{texture_path}"/>'''
        try:
            section = ET.fromstring(data)
            self.GDLPict.append(section)
        except:
            super().debug(f"could not create texture {texture.name} for object {self.name}. probably due to name issue.", 2)

        # Copy the texture file to the output subfolder alongside the converted XML.
        original_texture_path = texture.path
        path = output_folder + self.relative_path + os.sep + self.name + os.sep

        if not os.path.exists(path):
            os.makedirs(path)

        shutil.copy2(original_texture_path, path)

        return image_index

    @staticmethod
    def check_CDATA(section):
        """Ensure all GDL script sections are wrapped in CDATA sentinels before writing.

        Archicad requires CDATA wrappers around all script and metadata text fields.
        ET strips CDATA on parse; this method re-wraps the known GDL text sections
        with CDATA() sentinel elements before compile_xml() calls tree.write().

        The exhaustive tag list covers all script and text sections in Archicad object XML:
          MName, Description, Script_3D, Script_2D, Script_1D, Script_PR, Script_UI,
          Script_VL, Script_FWM, Script_BWM, Keywords, Comment

        For other sections, recurse into children to handle nested CDATA sections.
        NOTE: `x = 1` is dead code left from debugging.
        """
        x = 1  # Dead code - debugging remnant, harmless.
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
        """Write the processed object as a new XML file to the output folder.

        Rebuilds the XML tree from scratch using self.sections_list to preserve
        the original section order. GDLPict and Script_1D are always included
        even if they were not in the original (new GDLPict entries are added by
        add_gdlpict(); Script_1D may have been synthesized by get_script_1d()).

        check_CDATA() is applied to every section before appending to ensure
        CDATA wrappers are present on all GDL script fields.

        Output path mirrors the input subfolder structure under output_folder.
        """
        # Filter to only sections that exist on this instance (dir() returns all attrs).
        # Force-include GDLPict and Script_1D which may have been added during processing.
        attributes = [attr for attr in dir(self) if attr in self.sections_list + ["GDLPict", "Script_1D"]]

        tree = ET.ElementTree()
        root = ET.Element("Symbol")
        # Preserve original XML root attributes (MainGUID, SubType, etc.)
        for attrib, value in self.xml_data.attrib.items():
            root.attrib[attrib] = value

        for attr in attributes:
            # List sections (e.g. multiple GDLPict) are appended item by item.
            if isinstance(getattr(self, attr), list):
                for item in getattr(self, attr):
                    root.append(OBJET.check_CDATA(item))
            else:
                section = getattr(self, attr)
                root.append(OBJET.check_CDATA(section))

        tree._setroot(root)

        global output_folder
        output_path = output_folder + self.relative_path + "\\"
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        file_path = output_path + self.name + ".xml"

        # Write with UTF-8 encoding and XML declaration header.
        # The patched _serialize_xml ensures CDATA blocks are emitted correctly.
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
