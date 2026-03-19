import datetime
import bpy
import re

# xml_template.py: Generates the full Archicad GDL Library Object XML for a single mesh.
#
# The XML structure contains:
#   Script_1D: Constants (LOD level enum values)
#   Script_2D: 2D symbol (plan view) - either from mesh_to_symbol or PROJECT2 fallback
#   Script_3D: 3D mesh (GDL TEVE/EDGE/PGON body from mesh_to_gdl)
#   Script_PR: Properties script (empty)
#   Script_UI/VL: UI and value-list scripts for LOD/display parameters
#   ParamSection: Object parameters (A, B, ZZYZX dimensions + user-defined + surface overrides)
#   GDLPict: Embedded texture images (referenced by DEFINE TEXTURE in Script_3D)
#   Picture: Thumbnail preview PNG

def get_xml(object_name, is_placable:bool, symbol_script:str, mesh_script:str, bound_x:float, bound_y:float, bound_z:float, shift_z, lod, Textures_ids, surfaces = [], materials = [],  ac_version:int=43, thumbnail_path=None):
	'''
	object_index: 12 char, a-f, A-F, 0-9
	is_placable: boolean. appears or not in the search
	symbol_script: returned by mesh_to_symbol() - may be None, falls back to PROJECT2
	mesh_script: return by mesh_to_gdl()
	bound_x: X max dimension of object
	bound_y: Y max dimension of object
	bound_z: Z max dimension of object
	ac_version: Archicad version. Lookup online for correct number. Default AC25
	'''
	date = datetime.datetime.now()
	gdl_script = ""
	for item in mesh_script:
		gdl_script += item + "\n"


	# Defines the attributes parameters
	attributes_str = ""
	# old_guid_str: if set, reuse the GUID from a previous export (preserves Archicad object identity on re-export).
	old_guid_str = ""
	preferences = bpy.context.preferences.addons[__package__].preferences

	# (Commented-out GUID validation regex - was intended to validate old_GUID format)
	# guid_patern = re.compile("[0-9a-fA-F]{8}([+\-/*.,; ]*[0-9a-fA-F]{4}){2}([+\-/*.,; ]*[0-9a-fA-F]{2}){8}")

	for propattr in bpy.context.scene.archicad_converter_props.collection:
		flags = ""
		if propattr.hide_flag:
			flags += "<ParFlg_Hidden/>\n"
		if propattr.child_flag:
			flags += "<ParFlg_Child/>\n"
		if propattr.bold_flag:
			flags += "<ParFlg_BoldName/>\n"
		if propattr.unique_flag:
			flags += "<ParFlg_Unique/>\n"

		if propattr.ac_type == "String":
			if propattr.identifier == "old_GUID":
				# Special property: extract GUID to use as MainGUID instead of generating a new one.
				# This preserves the object's identity in Archicad across re-exports.
				# (Commented-out: guid_patern.match(propattr.String) validation)
				old_guid_str = propattr.String
				continue
			
			attributes_str += f"""
			<{propattr.ac_type} Name="{propattr.identifier}">
				<Description><![CDATA["{propattr.name}"]]></Description>
				{f'''<Flags>
					{flags}
				</Flags>''' if flags != "" else ''}
				<Value><![CDATA["{eval(f"propattr.{propattr.ac_type}")}"]]></Value>
			</{propattr.ac_type}>
	"""



		else:
			# NOTE: eval() is used here to dynamically read the property value by type name.
			# e.g. propattr.ac_type="Length" → eval("propattr.Length") → reads the Length float value.
			# This works because AC_single_prop defines one property per type name (Length, Angle, etc.).
			attributes_str += f"""
			<{propattr.ac_type} Name="{propattr.identifier}">
				<Description><![CDATA["{propattr.name}"]]></Description>
				{f'''<Flags>
					{flags}
				</Flags>''' if flags != "" else ''}
				<Value>{eval(f"propattr.{propattr.ac_type}")}</Value>
			</{propattr.ac_type}>
	"""
		

	parameter_surface = ""

	for sf_index, surface_title in enumerate(surfaces):
		# parameter_surface += f''''''
		parameter_surface += f'''
		<Material Name="{surface_title}">
			<Description><![CDATA["Surface {surface_title[3:]}"]]></Description>
			<Flags>
				<ParFlg_Child/>
			</Flags>
			<Value>{preferences.default_surface}</Value>
		</Material>

'''


	if thumbnail_path:
		thumbnail = f'<Picture MIME="image/png" SectVersion="19" SectionFlags="0" SubIdent="0" path="{object_name}_preview.png"/>'
	else:
		thumbnail = ''
	
	textures = ""

	for index, name in Textures_ids.items():
		textures += f'''
<GDLPict MIME="image/png" SectVersion="19" SectionFlags="0" SubIdent="{index}" path="{name}"/>
		'''


	# GUID format when no old_GUID is set:
	# "AC0000CF-0000-70D{lod}-{year}-00{month:02}{day:02}{hour:02}{min:02}{sec:02}"
	# e.g. lod=0 → "AC0000CF-0000-70D0-2024-001201143052"
	# The lod digit in segment 3 distinguishes LOD variants of the same export.
	# This timestamp-based GUID is NOT universally unique but is deterministic for a given export time.
	return f'''<?xml version="1.0" encoding="UTF-8"?>
<Symbol IsArchivable="false" IsPlaceable="{"true" if is_placable else "false"}" MainGUID="{old_guid_str if old_guid_str else f"AC0000CF-0000-70D{lod if lod else 0}-{date.year}-00{date.month:02}{date.day:02}{date.hour:02}{date.minute:02}{date.second:02}"}" MigrationValue="Normal" Owner="0" Signature="0" Version="{str(ac_version)}">
<Ancestry SectVersion="1" SectionFlags="0" SubIdent="0" Template="false">
	<MainGUID>F938E33A-329D-4A36-BE3E-85E126820996</MainGUID>
	<MainGUID>103E8D2C-8230-42E1-9597-46F84CCE28C0</MainGUID>
</Ancestry>

<!-- GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT -->

<Script_2D SectVersion="20" SectionFlags="0" SubIdent="0">
<![CDATA[
! MUL2 scales the 2D coordinate system so the symbol fits A×B regardless of original size.
! A and B are the Archicad object parameters (width/depth), set by the user in Archicad.
MUL2 A*{(1/bound_x) if bound_x else 0}, B*{(1/bound_y) if bound_y else 0}
pen     penAttribute_1
set line_type lineTypeAttribute_1
set fill fillAttribute_1
! ==============================================================================
! 2D Detail Level
! ==============================================================================


if _iDetlevel2D = OBJECT_SCHEMATIC then
	POLY2_B 5, 1+2+64, fillfgpen_1, fillbgpen_1, 
			A*(-0.5), B*(-0.5), 1+32,
			A*0.5, B*(-0.5), 1+32,
			A*0.5, B*0.5, 1+32,
			A*(-0.5), B*0.5, 1+32,
			A*(-0.5), B*(-0.5), -1
	end
endif


!!!--- Celui ci affiche la projection en 2D du 3D ---
! pen fillfgpen_1
! PROJECT2{"{2}"} 3, 270, 3+32+1024+16, fillbgpen_1
!END

!!!--- Celui ci affiche le contenu de "Symbole 2D" ---
!FRAGMENT2 1, 1
!END

!!!-------   Symbole 2D généré par l'extension --------

{symbol_script if symbol_script else """
! 2D generation was disabled for this object at export.
pen fillfgpen_1
PROJECT2{2} 3, 270, 3+32+1024+16, fillbgpen_1
END"""}
]]>
</Script_2D>

<!-- GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT -->

<Script_3D SectVersion="20" SectionFlags="0" SubIdent="0">
<![CDATA[
! ==============================================================================
! 3D Detail Level
! ==============================================================================


if _iDetlevel3D = OBJECT_SCHEMATIC then
	ADDX A*(-0.5)
	ADDY B*(-0.5)
	BLOCK A, B, ZZYZX
	end
endif


! ADDZ shifts the model up so its lowest point is at Z=0 (floor plane).
! shift_z = -min_z from mesh_to_gdl (the negated minimum vertex Z).
ADDZ {shift_z}
!ROTZ 180
! Scale the model to fit within A × B × ZZYZX (the Archicad parametric dimensions).
! Division by bound_* converts from absolute units to a normalized 0..1 space,
! then multiplied by A/B/ZZYZX to allow user-driven resizing in Archicad.
MULX A*{(1/bound_x) if bound_x else 0}
MULY B*{(1/bound_y) if bound_y else 0}
MULZ ZZYZX*{(1/bound_z) if bound_z else 0}
{gdl_script}
! EXIT declares the object's hotspot extents (height, width, depth) for Archicad snapping.
EXIT ZZYZX, A, B
]]>
</Script_3D>

<ParamSection SectVersion="27" SectionFlags="0" SubIdent="0">
	<ParamSectHeader>
		<AutoHotspots>true</AutoHotspots>
		<StatBits>
			<STBit_FixSize/>
			<STBit_Enable2DScriptDrawingOrder/>
		</StatBits>
		<WDLeftFrame>0</WDLeftFrame>
		<WDRightFrame>0</WDRightFrame>
		<WDTopFrame>0</WDTopFrame>
		<WDBotFrame>0</WDBotFrame>
		<LayFlags>65535</LayFlags>
		<WDMirrorThickness>0</WDMirrorThickness>
		<WDWallInset>0</WDWallInset>
	</ParamSectHeader>
	<Parameters>
		<Boolean Name="AC_show2DHotspotsIn3D">
			<Description><![CDATA["Afficher points chauds 2D en 3D"]]></Description>
			<Fix/>
			<Flags>
				<ParFlg_Hidden/>
			</Flags>
			<Value>1</Value>
		</Boolean>
		<Length Name="ac_bottomlevel">
			<Description><![CDATA["Niveau inférieur"]]></Description>
			<Fix/>
			<Flags>
				<ParFlg_Hidden/>
			</Flags>
			<Value>1</Value>
		</Length>
		<Length Name="ac_toplevel">
			<Description><![CDATA["Niveau supérieur"]]></Description>
			<Fix/>
			<Flags>
				<ParFlg_Hidden/>
			</Flags>
			<Value>0</Value>
		</Length>


		<Length Name="A">
			<Description><![CDATA["1ère dimension"]]></Description>
			<Fix/>
			<Value>{bound_x}</Value>
		</Length>
		<Length Name="B">
			<Description><![CDATA["2ème dimension"]]></Description>
			<Fix/>
			<Value>{bound_y}</Value>
		</Length>
		<Length Name="ZZYZX">
			<Description><![CDATA["Hauteur"]]></Description>
			<Fix/>
			<Value>{bound_z}</Value>
		</Length>
		
		<Title Name="DISPLAY_TITLE">
			<Description><![CDATA["AFFICHAGE"]]></Description>
		</Title>
		<Integer Name="iDetlevel3D">
			<Description><![CDATA["Affichage 3D"]]></Description>
			<Fix/>
			<Flags>
				<ParFlg_Child/>
			</Flags>
			<Value>1</Value>
		</Integer>
		<Integer Name="iDetlevel2D">
			<Description><![CDATA["Affichage plan"]]></Description>
			<Fix/>
			<Flags>
				<ParFlg_Child/>
			</Flags>
			<Value>1</Value>
		</Integer>
		

		{attributes_str}
		
		<Title Name="SURFACE_TITLE">
			<Description><![CDATA["SURFACES"]]></Description>
		</Title>
		{parameter_surface}

	</Parameters>
</ParamSection>

<Copyright SectVersion="1" SectionFlags="0" SubIdent="0">
	<Author></Author>
	<License>
		<Type>CC BY</Type>
		<Version>4.0</Version>
	</License>
</Copyright>

<CalledMacros SectVersion="2" SectionFlags="0" SubIdent="0">
</CalledMacros>

<!-- GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT -->

<Script_1D SectVersion="20" SectionFlags="0" SubIdent="0">
<![CDATA[
! const values for parameter iDetlevel2D and/or iDetLev3D
OBJECT_SCHEMATIC	= 1
OBJECT_SIMPLIFIED	= 2
OBJECT_FULL			= 3

_iDetlevel2D = OBJECT_FULL
_iDetlevel3D = OBJECT_FULL
_temp = 3

IF iDetlevel2D = 0 THEN
	if GLOB_SCRIPT_TYPE = 2 then
	success = LIBRARYGLOBAL("Objects_MVOSettings.gsm", "iObjectDetlevel2D", _temp) ! Archicad 28 libpart
		if success THEN
			_iDetlevel2D = _temp
		endif
	success = LIBRARYGLOBAL("DetlevelFunctionMacro.gsm", "iDetlevel2D", _temp) ! Archicad 27 monolithic library
		if success THEN
			_iDetlevel2D = _temp
		endif
	endif
ELSE
	_iDetlevel2D = iDetlevel2D
ENDIF

IF iDetlevel3D = 0 THEN
	if GLOB_SCRIPT_TYPE = 3 then
	success = LIBRARYGLOBAL("Objects_MVOSettings.gsm", "iObjectDetlevel3D", _temp) ! Archicad 28 libpart
		if success THEN
			_iDetlevel3D = _temp
		endif
	success = LIBRARYGLOBAL("DetlevelFunctionMacro.gsm", "iDetlevel3D", _temp) ! Archicad 27 monolithic library
		if success THEN
			_iDetlevel3D = _temp
		endif
	endif
ELSE
	_iDetlevel3D = iDetlevel3D
ENDIF
]]>
</Script_1D>

<!-- GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT -->

<Script_PR SectVersion="20" SectionFlags="0" SubIdent="0">
<![CDATA[]]>
</Script_PR>

<!-- GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT -->

<Script_UI SectVersion="20" SectionFlags="0" SubIdent="0">
<![CDATA[]]>
</Script_UI>

<!-- GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT -->

<Script_VL SectVersion="20" SectionFlags="0" SubIdent="0">
<![CDATA[
values{"{2}"} "iDetlevel3D",
			0, `Selon options vue`,
			3, `Détaillé`,
			1, "Simple"
			
values{"{2}"} "iDetlevel2D",
			0, `Selon options vue`,
			3, `Détaillé`,
			1, "Simple"
]]>
</Script_VL>

<!-- GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT -->

<Script_FWM SectVersion="20" SectionFlags="0" SubIdent="0">
<![CDATA[]]>
</Script_FWM>

<!-- GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT -->

<Script_BWM SectVersion="20" SectionFlags="0" SubIdent="0">
<![CDATA[]]>
</Script_BWM>

<Keywords SectVersion="1" SectionFlags="0" SubIdent="0">
<![CDATA[]]>
</Keywords>

<Comment SectVersion="20" SectionFlags="0" SubIdent="0">
<![CDATA[]]>
</Comment>

{thumbnail}
{textures}


</Symbol>
'''