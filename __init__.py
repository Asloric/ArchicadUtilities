import os
import bpy

from . import interface, operators

bl_info = {
    "name": "Archicad exporter",
    "author": "Clovis Flayols",
    "version": (0, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Toolshelf",
    "description": "Archicad object automatic creation. With a bit of luck.",
    "category": "Export",
}


def register():
    operators.register()
    interface.register()

def unregister():
    operators.unregister()
    interface.unregister()

if __name__ == "__main__":
    register()
