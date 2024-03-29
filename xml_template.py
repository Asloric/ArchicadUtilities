import datetime
import bpy

def get_xml(object_name, is_placable:bool, symbol_script:str, mesh_script:str, bound_x:float, bound_y:float, bound_z:float, shift_z, lod, Textures_ids, surfaces = [], materials = [],  ac_version:int=43, thumbnail_path=None):
	'''
	object_index: 12 char, a-f, A-F, 0-9
	is_placable: boolean. appears or not in the search
	symbol_script: returned by mesh_to_symbol()
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


	# Defines the attrubues parameters
	attributes_str = ""
	preferences = bpy.context.preferences.addons[__package__].preferences
	for propattr in bpy.context.window_manager.archicad_converter_props.collection:
		flags = ""
		if propattr.hide_flag:
			flags += "<ParFlg_Hidden/>\n"
		if propattr.child_flag:
			flags += "<ParFlg_Child/>\n"
		if propattr.bold_flag:
			flags += "<ParFlg_BoldName/>\n"
		if propattr.unique_flag:
			flags += "<ParFlg_Unique/>\n"


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


	return f'''<?xml version="1.0" encoding="UTF-8"?>
<Symbol IsArchivable="false" IsPlaceable="{"true" if is_placable else "false"}" MainGUID="AC0000CF-0000-70D{lod if lod else 0}-{date.year}-00{date.month:02}{date.day:02}{date.hour:02}{date.minute:02}{date.second:02}" MigrationValue="Normal" Owner="0" Signature="0" Version="{str(ac_version)}">
<Ancestry SectVersion="1" SectionFlags="0" SubIdent="0" Template="false">
	<MainGUID>F938E33A-329D-4A36-BE3E-85E126820996</MainGUID>
	<MainGUID>103E8D2C-8230-42E1-9597-46F84CCE28C0</MainGUID>
</Ancestry>

<!-- GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT -->

<Script_2D SectVersion="20" SectionFlags="0" SubIdent="0">
<![CDATA[
pen     penAttribute_1
set line_type lineTypeAttribute_1
set fill fillAttribute_1
!FRAGMENT2 1, 1
{symbol_script}
]]>
</Script_2D>

<!-- GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT -->

<Script_3D SectVersion="20" SectionFlags="0" SubIdent="0">
<![CDATA[
ADDZ {shift_z}
!ROTZ 180
MULX A*{(1/bound_x) if bound_x else 0}
MULY B*{(1/bound_y) if bound_y else 0}
MULZ ZZYZX*{(1/bound_z) if bound_z else 0}
{gdl_script}
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
<![CDATA[]]>
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
<![CDATA[]]>
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