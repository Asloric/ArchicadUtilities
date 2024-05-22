import bpy, inspect
from . import utils

# This file handles the properties of objects. Those properties are the mirror of what can be seen in the "principal" tab in archicad. 
       
class AC_export_properties(bpy.types.PropertyGroup):

    object_name: bpy.props.StringProperty(name="Object name", default="")
    is_placable: bpy.props.BoolProperty(default=True, description="Will the object be viewable in search popup")
    smooth_angle: bpy.props.FloatProperty(name="smooth angle", default=1.0, subtype="ANGLE", description="Below this angle, edges will be smooth if not marked as sharp.")
    save_path: bpy.props.StringProperty(name="save to", subtype="DIR_PATH", default="C:\\")
    export_lod: bpy.props.BoolProperty(name="export as LOD", default=False)
    lod_1: bpy.props.PointerProperty(name="Coarse", type=bpy.types.Object)
    lod_0: bpy.props.PointerProperty(name="Detailed", type=bpy.types.Object)
    lod_0: bpy.props.PointerProperty(name="Detailed", type=bpy.types.Object)


    def register():
        bpy.types.Scene.acaccf = bpy.props.PointerProperty(type=AC_export_properties)
    
    def unregister():
        del bpy.types.Scene.acaccf


class AC_single_prop(bpy.types.PropertyGroup):
    def prop_enforce_name(self, context):
        def avoide_duplicate(identifier, identifier_suffix):
            # create the name, then check if it exists
            if identifier_suffix > 0:
                new_identifier = identifier + "_" + str(identifier_suffix)
            else:
                new_identifier = identifier

            for item in bpy.context.scene.archicad_converter_props.collection:
                if item.name == new_identifier and item != self:
                    identifier_suffix += 1
                    return avoide_duplicate(identifier, identifier_suffix)

            return new_identifier
        
        if len(inspect.stack()) <= 2:
            name_suffix = 0
            new_name = utils.cleanString(self.identifier)
            new_name = avoide_duplicate(new_name, name_suffix)
            self.identifier = new_name

    identifier: bpy.props.StringProperty(name="identifier", default="PropertyAttribute", description="identifier of the property. must be unique", update=prop_enforce_name)
    name: bpy.props.StringProperty(name="name", description="name of the property")
    ac_type: bpy.props.EnumProperty(items=[
        ("Length", "Length", "Length"),
        ("Angle", "Angle", "Angle"),
        ("RealNum", "Float", "Float"),
        ("Integer", "Integer", "Integer"),
        ("Boolean", "Boolean", "Boolean"),
        ("String", "String", "String"),
        ("PenColor", "Pen", "Pen"),
        ("LineType", "Line type", "Line type"),
        ("FillPattern", "Fill pattern", "Fill pattern"),
        ("Profile", "Profile", "Profile"),
        ("Material", "Surface", "Surface"),
        ("BuildingMaterial", "Building material", "Building material"),
        ("Title", "Title", "Title"),
        ("Separator", "Separator", "Separator")
    ])
    Length: bpy.props.FloatProperty(name="value", subtype="DISTANCE")
    Angle: bpy.props.FloatProperty(name="value", subtype='ANGLE')
    RealNum: bpy.props.FloatProperty(name="value")
    Integer: bpy.props.IntProperty(name="value")
    Boolean: bpy.props.BoolProperty(name="value")
    String: bpy.props.StringProperty(name="value")
    PenColor: bpy.props.IntProperty(name="value")
    LineType: bpy.props.IntProperty(name="value")
    FillPattern: bpy.props.IntProperty(name="value")
    Profile: bpy.props.IntProperty(name="value")
    Material: bpy.props.IntProperty(name="value")
    BuildingMaterial: bpy.props.IntProperty(name="value")
    Title: bpy.props.StringProperty(name="value")
    Separator: bpy.props.StringProperty(name="value")

    hide_flag: bpy.props.BoolProperty(name="hide", description="hide from interface")
    child_flag: bpy.props.BoolProperty(name="child", description="is child of above attribute")
    bold_flag: bpy.props.BoolProperty(name="bold", description="text will appear bold")
    unique_flag: bpy.props.BoolProperty(name="unique", description="I don't know.")

class AC_PropertyGroup_props(bpy.types.PropertyGroup):

    def add_handler(function, handler):
        if not function in handler:
            handler.append(function)

    def remove_handler(function, handler):
        if function in handler:
            handler.remove(function)



    def ensure_default_props(self, context):
        preferences = bpy.context.preferences.addons[__package__].preferences
        # Ensure the default props are still in the list

        # build list of names
        name_list = [prop.identifier for prop in self.collection]

        if not "PenAttribute_1" in name_list:
            prop = bpy.context.scene.archicad_converter_props.collection.add()
            prop.name = "Stylo lignes"
            prop.identifier = "PenAttribute_1"
            prop.ac_type = "PenColor"
            prop.PenColor = preferences.default_pen
            prop.child_flag = True

        if not "lineTypeAttribute_1" in name_list:
            prop = bpy.context.scene.archicad_converter_props.collection.add()
            prop.name = "Type de lignes"
            prop.identifier = "lineTypeAttribute_1"
            prop.ac_type = "LineType"
            prop.LineType = preferences.default_line
            prop.child_flag = True

        if not "fillAttribute_1" in name_list:
            prop = bpy.context.scene.archicad_converter_props.collection.add()
            prop.name = "Hachure"
            prop.identifier = "fillAttribute_1"
            prop.ac_type = "FillPattern"
            prop.FillPattern = preferences.default_hatch
            prop.child_flag = True

        if not "fillbgpen_1" in name_list:
            prop = bpy.context.scene.archicad_converter_props.collection.add()
            prop.name = "Stylo Fond"
            prop.identifier = "fillbgpen_1"
            prop.ac_type = "PenColor"
            prop.PenColor = preferences.default_pen_bg_hatch
            prop.child_flag = True

        if not "fillfgpen_1" in name_list:
            prop = bpy.context.scene.archicad_converter_props.collection.add()
            prop.name = "Stylo Premier plan"
            prop.identifier = "fillfgpen_1"
            prop.ac_type = "PenColor"
            prop.PenColor = preferences.default_pen_fg_hatch
            prop.child_flag = True

        if not "product_reference" in name_list:
            prop = bpy.context.scene.archicad_converter_props.collection.add()
            prop.name = "Reference produit"
            prop.identifier = "product_reference"
            prop.ac_type = "String"
            prop.String = ""
            prop.child_flag = False

        if not "old_GUID" in name_list:
            prop = bpy.context.scene.archicad_converter_props.collection.add()
            prop.name = "ancien GUID"
            prop.identifier = "old_GUID"
            prop.ac_type = "String"
            prop.String = ""


    collection: bpy.props.CollectionProperty(type=AC_single_prop)
    active_user_index: bpy.props.IntProperty(update=ensure_default_props)

    def register():
        bpy.types.Scene.archicad_converter_props = bpy.props.PointerProperty(type=AC_PropertyGroup_props)
        AC_PropertyGroup_props.add_handler(AC_PropertyGroup_props.ensure_default_props, bpy.app.handlers.load_post)
    
    def unregister():
        AC_PropertyGroup_props.remove_handler(AC_PropertyGroup_props.ensure_default_props, bpy.app.handlers.load_post)
        del bpy.types.Scene.archicad_converter_props





class AC_UL_props(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if item.name in ["Stylo lignes", "Type de lignes", "Hachure", "Stylo Fond", "Stylo Premier plan", "ancien GUID", "Reference produit"]:
            layout.label(text=item.name)
        else:
            layout.prop(item, "identifier", emboss=False, text="")
        layout.separator()




classes = [
    AC_export_properties,
    AC_single_prop,
    AC_PropertyGroup_props,
    AC_UL_props,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)




def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
