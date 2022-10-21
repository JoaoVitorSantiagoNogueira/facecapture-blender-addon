#!/usr/bin/env python3

bl_info = {
    "name": "Face capture",
    "author": "Leonardo Carvalho, Bruno Sumar, João Vitor Santiago, Sabrina Sampaio, Wanderley Rangel, Gabriel Azevedo",
    "version": (1, 0),
    "blender": (3, 1, 0),
    "location": "View 3D > Sidebar > Face capture tab",
    "description": "Capture facial expressions from camera and transfer the expression to a mesh with shape keys.",
    "warning": "",
    "doc_url": "",
    "category": "Animation",
}

import bpy
from bpy_extras.object_utils import AddObjectHelper
from bpy.props import (
    FloatProperty,
    IntProperty,
    BoolProperty
)

import importlib

from facecapture import face_capture_modal
if "face_capture_modal" in locals():
    importlib.reload(face_capture_modal)

from facecapture import Blendshape_retarget_manual 
if "Blendshape_retarget_manual" in locals():
    importlib.reload(Blendshape_retarget_manual)

class VIEW3D_face_capture_menu(bpy.types.Panel):
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Face capture"
    bl_label = "Face capture menu"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        fc = context.scene.fc_settings

        # Settings
        col = layout.column()
        col.use_property_split = True
        col.label(text="Settings:")

        # Capture frames per second
        row = col.row()
        row.prop(fc,'fps')
        row.enabled = not fc.is_fc_on
        
        # Camera device index
        row = col.row()
        row.prop(fc,'camera_index')
        row.enabled = not fc.is_fc_on

        # Automatic keyframe insertion
        row = col.row()
        row.prop(fc,'auto_insert')

        # Open window to show captured image
        row = col.row()
        row.prop(fc,'show_cam')
        
        # Landmarks mesh
        
        #row = col.row()
        #row.prop(fc,'landmark_mesh')
        
        # Face capture button
        row = layout.row()
        row.scale_y = 2.
        row.prop(fc,'is_fc_on',
                 toggle=True,
                 icon='CAMERA_DATA',
                 text= 'Stop capture' if fc.is_fc_on else "Init capture"
                 )

def toggle_fc(self, context):
    if context.scene.fc_settings.is_fc_on:
        bpy.ops.landmark.facecapture()

class FaceCapureSettings(bpy.types.PropertyGroup):
    fps: bpy.props.FloatProperty(
        default=30,
        name="Frames per second",
        description="Number of captured frames per second",
    )
    camera_index: bpy.props.IntProperty(
        default=0,
        name="Camera",
        description="Camera device index used in capture",
    )
    is_fc_on: BoolProperty(
        default=False,
        name="Capture state",
        description="Indicates if capture is active",
        update=toggle_fc
    )
    auto_insert: BoolProperty(
        default=False,
        name="Insert keyframes",
        description="Controls automatic insertion of keyframes",
    )
    show_cam: BoolProperty(
        default=False,
        name="Show image",
        description="Controls exhibition of the imagem used for face capture",
    )
    landmark_mesh: bpy.props.PointerProperty(
        name="Landmarks mesh", 
        description="Mesh with tracked landmark points",
        type=bpy.types.Object
    )
    blendshape_mesh: bpy.props.PointerProperty(
        name="Blendshape mesh", 
        description="Mesh with shape keys (or blendshapes) created from landmarks mesh",
        type=bpy.types.Object
    )
    retarget_mesh: bpy.props.PointerProperty(
        name="Target Mesh",
        description="Another mesh with shape keys transformed from the blendshape mesh",
        type=bpy.types.Object
    )

    retarget_shape_key: bpy.props.StringProperty(
        default="Basis",
        name="Retarget Blendshape",
        description="Shape key name",
    )
    tolerance: bpy.props.FloatProperty(
        default=0.5,
        name="Tolerance",
        description="Tolerance used in automatic insertion of shape keys",
    )

class duplicate_and_assign(bpy.types.Operator):
    '''Creates a copy of landmarks mesh and assign it to blendshape mesh'''
    bl_idname = "landmark.duplicate_and_assign"
    bl_label = "Duplicate and Assign"

    def execute(self, context):
        fc = context.scene.fc_settings
        cpy = fc.landmark_mesh.copy()
        cpy.data = fc.landmark_mesh.data.copy()
        cpy.name = "Blendshape mesh"

        bpy.context.collection.objects.link(cpy)
        fc.blendshape_mesh = cpy

        return {'FINISHED'}

class add_shape_keys(bpy.types.Operator):
    '''Add current face expression as a shape key'''
    bl_idname = "landmark.add_shape_keys"
    bl_label = "Add Shape Key"  

    def execute(self, context):
        fc = context.scene.fc_settings

        bpy.context.view_layer.objects.active = fc.blendshape_mesh
        fc.landmark_mesh.select_set(True)

        n = 0

        for group in fc.blendshape_mesh.vertex_groups:
            # if group is empty, ignore it
            if not any(group.index in [g.group for g in v.groups] for v in fc.blendshape_mesh.data.vertices):
                continue

            bpy.ops.object.join_shapes()
            shape_key = fc.blendshape_mesh.data.shape_keys.key_blocks[-1]
            shape_key.name = 'key_' + group.name
            shape_key.vertex_group = group.name
            n = n+1
        
        if n == 0:
            bpy.ops.object.join_shapes()
            shape_key = fc.blendshape_mesh.data.shape_keys.key_blocks[-1]
            shape_key.name = 'key'

        return {'FINISHED'}

class VIEW3D_shape_keys_menu(bpy.types.Panel):
    bl_idname = "SCENE_PT_layout_shape_keys"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Face capture"
    bl_label = "shape keys menu"


    def draw(self, context):
        layout = self.layout
        scene = context.scene

        fc = context.scene.fc_settings
        
        # Blendshape mesh
        row = layout.row()
        row.use_property_split = True
        row.prop(fc,'blendshape_mesh')

        # Automatic shape key insertion tolerance
        row = layout.row()
        row.use_property_split = True
        row.prop(fc, 'tolerance')

        # Add or assign button
        row = layout.row()
        row.scale_y = 2.
        if fc.landmark_mesh is not None and fc.blendshape_mesh is not None:
            row.operator("landmark.add_shape_keys")
        else:
            row.operator("landmark.duplicate_and_assign")

class VIEW3D_retargeting_menu(bpy.types.Panel):
    bl_idname = "SCENE_PT_layout_retargeting"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Face capture"
    bl_label = "Retargeting menu"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        fc = context.scene.fc_settings

        col = layout.column()
        col.use_property_split = True
        col.label(text="Settings:")
        
        # Target blendshape mesh
        row = col.row()
        row.prop(fc,'retarget_mesh')

        # Current blendshape
        if fc.blendshape_mesh is not None and fc.blendshape_mesh.data.shape_keys is not None:
            row = col.row()
            row.prop_search(fc, 'retarget_shape_key', fc.blendshape_mesh.data.shape_keys, 'key_blocks')

        # Calculate conversion values
        row = layout.row()
        row.scale_y = 2.
        row.operator("retarget.blendshapes_single")

        # Apply changes to final model
        row = layout.row()
        row.operator("retarget.blendshapes_update")

__classes__ = (face_capture_modal.FaceCaptureModal, VIEW3D_face_capture_menu, FaceCapureSettings, duplicate_and_assign, add_shape_keys,
            VIEW3D_shape_keys_menu, Blendshape_retarget_manual.Blendshape_retarget_single_blendshape, Blendshape_retarget_manual.Blendshape_target_update, VIEW3D_retargeting_menu)

def register():
    for cls in __classes__:
        bpy.utils.register_class(cls)
    bpy.types.Scene.fc_settings = bpy.props.PointerProperty(type=FaceCapureSettings)

def unregister():
    for cls in reversed (__classes__):
         bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
