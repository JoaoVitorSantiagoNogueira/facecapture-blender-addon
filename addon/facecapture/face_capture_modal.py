import importlib
import bpy
import bmesh
import cv2
import mediapipe as mp
import numpy as np
from bpy_extras.object_utils import AddObjectHelper
from bpy_extras import object_utils
from bpy.props import (BoolProperty)
import time


from . import Blendshape
if "Blendshape" in locals():
    importlib.reload(Blendshape)

from . import mediapipe_capture
if "mediapipe_capture" in locals():
    importlib.reload(mediapipe_capture)

from facecapture import createLandmarks as cl
if "cl" in locals():
    importlib.reload(cl)

asyncCapture = mediapipe_capture.asyncCapture
BlendshapeMesh = Blendshape.BlendshapeMesh

from bpy.props import (
    FloatProperty,
)

# Utils
def convertBlenderObj(obj) :
    list = []

    if obj.data.shape_keys is None:
        verts = [v.co for v in obj.data.vertices]
        list.append(verts)
    else:
        # With shape keys
        kbs = obj.data.shape_keys.key_blocks

        base_verts = kbs[0].data

        for sk in kbs :
            group_name = sk.vertex_group
            verts = []
            for i,vert in enumerate(sk.data) :
                a = base_verts[i].co
                b = vert.co

                if group_name == '':
                    verts.append(b)
                else:
                    try:
                        w = obj.vertex_groups[group_name].weight(i)
                    except:
                        w = 0
                    verts.append(a + w*(b-a))
            list.append(verts)

    return np.array(list)

def updateWeightsBlender(obj, weights) :
    if obj.data.shape_keys is None:
        return

    kbs = obj.data.shape_keys.key_blocks
    for i, sk in enumerate(kbs[1:]) :
        sk.value = weights[i]

def normalize_vertices(data, face):
    lms = np.matrix(face['metric_landmarks'].T)
    data.vertices.foreach_set('co', lms.A1)
    data.update()
    
    return lms
        
def add_shape_keys(fc):
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

def print_time(label, time0, time1, total_time):
    dif = time1 - time0
    print(label, " {:20.10f}s = {:15.5f}%".format(dif, 100*dif/total_time))

class FaceCaptureModal(bpy.types.Operator):
    """Face capture landmark to mesh"""
    bl_idname = "landmark.facecapture"
    bl_label = "Face capture to mesh"
    bl_options = {'REGISTER', 'UNDO'}

    _mesh = None
    _timer = None
    _capture = None
    _endCapture = None

    def update_mesh(self, blendshape_mesh_obj):
        shape_keys = blendshape_mesh_obj.data.shape_keys
        nb = 0 if shape_keys is None else len(shape_keys.key_blocks)
        nw = 0 if self._mesh is None else len(self._mesh.weights)+1
        if self._mesh is None or nw != nb:
            self._mesh = BlendshapeMesh(convertBlenderObj(blendshape_mesh_obj))

    def calculate_weights(self, blendshape_mesh_obj, lms):
        self.update_mesh(blendshape_mesh_obj)

        weights, error = self._mesh.get_weights(lms)
        updateWeightsBlender(blendshape_mesh_obj, weights)

        return error

    def modal(self, context, event):
        fc = context.scene.fc_settings
        if event.type in {'RIGHTMOUSE', 'ESC'} or not fc.is_fc_on:
            self.cancel(context)
            return {'CANCELLED'}

        blendshape_mesh_obj = context.scene.fc_settings.blendshape_mesh
        landmarks_mesh_obj = context.scene.fc_settings.landmark_mesh

        if event.type == 'TIMER':
            try:
                time0 = time.time()
                faces, close = self._capture(fc.show_cam)
                time1 = time.time()

                if close:
                    fc.show_cam = False

                if len(faces) == 0:
                    return {'PASS_THROUGH'}

                # Use first face found
                lms = normalize_vertices(landmarks_mesh_obj.data, faces[0])
                time2 = time.time()

                if blendshape_mesh_obj is None:
                    return {'PASS_THROUGH'}

                error = self.calculate_weights(blendshape_mesh_obj, lms)
                #print("error ", error)
                if error > fc.tolerance:
                    add_shape_keys(fc)
                time3 = time.time()
        
                total_time = time3 - time0
                print_time("d1    ", time0, time1, total_time)
                print_time("d2    ", time1, time2, total_time)
                print_time("d3    ", time2, time3, total_time)
                print_time("Total:", time0, time3, total_time)
                print("{:30.10f} fps".format(1/total_time))

            except Exception as e :
                self.cancel(context)
                print("\n>> Error when updating mesh\n")
                print(e)
                return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        fps = 1.0/context.scene.fc_settings.fps
        self._timer = wm.event_timer_add(fps, window=context.window)
        wm.modal_handler_add(self)

        try:
            if context.scene.fc_settings.landmark_mesh is None:
                mesh = cl.createLandmarks(context)
                obj = object_utils.object_data_add(context, mesh)
                context.scene.fc_settings.landmark_mesh = obj 

            self._capture, self._endCapture = asyncCapture(context.scene.fc_settings.camera_index)
        except:
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}


    def cancel(self, context):
        # free mediapipe resources
        self._endCapture()
        self._capture = None
        self._endCapture = None
        # Unlink modal event
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        # Update menu
        fc = context.scene.fc_settings
        fc.is_fc_on = False
