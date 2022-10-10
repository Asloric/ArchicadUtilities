import datetime
import bpy

def get_xml(object_name:str, is_placable:bool, bound_x:float, bound_y:float, bound_z:float, surfaces = [], materials = [], ac_version:int=43):
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


	preferences = bpy.context.preferences.addons[__package__].preferences

	parameter_surface = ""

	for surface_title in surfaces:
		parameter_surface += f'''

		<Boolean Name="{"ovr_" + surface_title}">
			<Description><![CDATA["Remplacer surface"]]></Description>
			<Fix/>
			<Flags>
			</Flags>
			<Value>0</Value>
		</Boolean>

		<Material Name="{surface_title}">
			<Description><![CDATA["Surface {surface_title[3:]}"]]></Description>
			<Flags>
				<ParFlg_Child/>
			</Flags>
			<Value>{preferences.default_surface}</Value>
		</Material>

'''

	parameter_material = ""

	for material_title in materials:
		parameter_surface += f'''
		<BuildingMaterial Name="{material_title}">
			<Description><![CDATA["{material_title}"]]></Description>
			<Flags>
				<ParFlg_Child/>
			</Flags>
			<Value>{preferences.default_material}</Value>
		</BuildingMaterial>
'''


	return f'''<?xml version="1.0" encoding="UTF-8"?>
<Symbol IsArchivable="false" IsPlaceable="{"true" if is_placable else "false"}" MainGUID="AC0000CF-0000-70DA-{date.year}-00{date.month:02}{date.day:02}{date.hour:02}{date.minute:02}{date.second:02}" MigrationValue="Normal" Owner="0" Signature="0" Version="{str(ac_version)}">
<Ancestry SectVersion="1" SectionFlags="0" SubIdent="0" Template="false">
	<MainGUID>F938E33A-329D-4A36-BE3E-85E126820996</MainGUID>
	<MainGUID>103E8D2C-8230-42E1-9597-46F84CCE28C0</MainGUID>
</Ancestry>

<!-- GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT -->

<Script_3D SectVersion="20" SectionFlags="0" SubIdent="0">
<![CDATA[
_macro_choose = macro_choose

if macro_choose = 4 then
n = libraryglobal('LODSettings','macro_choose',_macro_choose)

endif 


call macro[_macro_choose] parameters all



dim stMacro_choose[],imacro_choose[]

stMacro_choose[1] = 'Very Simple Model'
stMacro_choose[2] = 'Simple Model'
stMacro_choose[3] = 'Detailed Model'
stMacro_choose[4] = 'MVO'

]]>
</Script_3D>

<!-- GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT -->

<Script_2D SectVersion="20" SectionFlags="0" SubIdent="0">
<![CDATA[
_macro_choose = macro_choose

if macro_choose = 4 then
n = libraryglobal('LODSettings','macro_choose',_macro_choose)

endif 


call macro[_macro_choose] parameters all



dim stMacro_choose[],imacro_choose[]

stMacro_choose[1] = 'Very Simple Model'
stMacro_choose[2] = 'Simple Model'
stMacro_choose[3] = 'Detailed Model'
stMacro_choose[4] = 'MVO'

!!! Comment out the above code and uncomment the line below to enable 2d symbol.
!FRAGMENT2 ALL, 0
]]>
</Script_2D>

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
<![CDATA[
    dim expr_page2[][] !#params2
    idx = 1


    expr_page2[idx][1] = "Modèle à afficher:"
    expr_page2[idx][2] = "macro_choose"
    idx=idx+1



!    expr_page2[idx][1] = "Elements source:"
!    expr_page2[idx][2] = "macro"
!    idx=idx+1
	!--------------------------------------------------------Activate those 3 lines to edit the LODs from UI
    

    iaf     = -2 !innfield adjust factor
    marginX = 5
    marginY = 0
    fieldHeight = 15    
    fieldWidth  = 120
    inFieldWidth  = 250
    inFieldWidthShort  = 50
    lineSpace   = 15
    padd = 3.5



        UI_STYLE 0,0


        FOR j = 0 TO VARDIM1(expr_page2) - 1 

            textLine = padd * marginY + j * (fieldHeight + lineSpace)
            
            UI_OUTFIELD expr_page2[j+1][1], 
                        marginX+marginX/2,
                        textLine, 
                        fieldWidth, 
                        fieldHeight,
                        0


            UI_INFIELD  expr_page2[j+1][2], 
                        marginX*2 + fieldWidth,
                        textLine+iaf, 
                        inFieldWidth, 
                        fieldHeight
            
            
        NEXT j

]]>
</Script_UI>

<!-- GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT ===== GDL SCRIPT -->

<Script_VL SectVersion="20" SectionFlags="0" SubIdent="0">
<![CDATA[
dim stMacro_choose[],imacro_choose[]

stMacro_choose[1] = 'Very Simple Model'
stMacro_choose[2] = 'Simple Model'
stMacro_choose[3] = 'Detailed Model'
stMacro_choose[4] = 'Based on Model View Options'

for i = 1 to vardim1(stMacro_choose)
	imacro_choose[i] = i
next i


values{"{2}"} 'macro_choose' 	1,stMacro_choose[1],
							2,stMacro_choose[2],
							3,stMacro_choose[3],
							4,stMacro_choose[4]



hideparameter "macro", "macro_choose"
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

<ParamSection SectVersion="27" SectionFlags="0" SubIdent="0">
	<ParamSectHeader>
		<AutoHotspots>false</AutoHotspots>
		<StatBits>
			<STBit_FixSize/>
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
		<Integer Name="macro_choose">
			<Description><![CDATA[""]]></Description>
			<Value>4</Value>
		</Integer>
		<String Name="macro">
			<Description><![CDATA[""]]></Description>
			<ArrayValues FirstDimension="3" SecondDimension="0">
				<AVal Row="1"><![CDATA["{object_name}_LOD1"]]></AVal>
				<AVal Row="2"><![CDATA["{object_name}_LOD1"]]></AVal>
				<AVal Row="3"><![CDATA["{object_name}_LOD0"]]></AVal>
			</ArrayValues>
		</String>
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
	


		<!-- PEN_TITLE: PARAMETER BLOCK ===== PARAMETER BLOCK ===== PARAMETER BLOCK ===== PARAMETER BLOCK -->

		<Title Name="PEN_TITLE">
			<Description><![CDATA["STYLOS"]]></Description>
		</Title>
		<PenColor Name="penAttribute_1">
			<Description><![CDATA["Stylo 1"]]></Description>
			<Flags>
				<ParFlg_Child/>
			</Flags>
			<Value>{preferences.default_pen}</Value>
		</PenColor>


		<!-- LINETYPE_TITLE: PARAMETER BLOCK ===== PARAMETER BLOCK ===== PARAMETER BLOCK ===== PARAMETER BLOCK -->

		<Title Name="LINETYPE_TITLE">
			<Description><![CDATA["LIGNES"]]></Description>
		</Title>
		<LineType Name="lineTypeAttribute_1">
			<Description><![CDATA["Ligne 1"]]></Description>
			<Flags>
				<ParFlg_Child/>
			</Flags>
			<Value>{preferences.default_line}</Value>
		</LineType>


		<!-- BUILDING_MATERIAL_TITLE: PARAMETER BLOCK ===== PARAMETER BLOCK ===== PARAMETER BLOCK ===== PARAMETER BLOCK -->

		<Title Name="MATERIAL_TITLE">
			<Description><![CDATA["MATERIAUX"]]></Description>
		</Title>
		{parameter_material}


		<!-- MATERIAL_TITLE: PARAMETER BLOCK ===== PARAMETER BLOCK ===== PARAMETER BLOCK ===== PARAMETER BLOCK -->

		<Title Name="SURFACE_TITLE">
			<Description><![CDATA["SURFACES"]]></Description>
		</Title>
		{parameter_surface}


	</Parameters>
</ParamSection>

<Copyright SectVersion="1" SectionFlags="0" SubIdent="0">
	<Author></Author>
	<License>
		<Type>CC0</Type>
		<Version>1.0</Version>
	</License>
</Copyright>

<Keywords SectVersion="1" SectionFlags="0" SubIdent="0">
<![CDATA[]]>
</Keywords>

<Comment SectVersion="20" SectionFlags="0" SubIdent="0">
<![CDATA[]]>
</Comment>


<Drawing Ordering="DrawQueue" SectVersion="36" SectionFlags="0" SubIdent="0">
</Drawing>

</Symbol>
'''
# THIS WAS LINE 256.  USE IT FOR PREVIEW
#<Picture MIME="image/png" SectVersion="19" SectionFlags="0" SubIdent="0" path="Chaises/Tabouret Classy 1097/Picture_0.png"/>
