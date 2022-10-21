#!/usr/bin/env python3

import bpy
import bmesh
from bpy_extras.object_utils import AddObjectHelper

from . import landmarks as lm

def createLandmarks(context):
    mesh = bpy.data.meshes.new("Face landmarks")
    bm = bmesh.new()

    # Adiciona pontos na malha
    verts = [(x/468,0.,0.) for x in range(0,468)]
    for v in lm.verts:
        bm.verts.new(v)

    bVerts = [v for v in bm.verts]

    # Adiciona arestas na malha (desnecessário no momento)
    # bEdges = [(bVerts[i], bVerts[j]) for (i,j) in lm.edges]
    # for e in bEdges:
    # bm.edges.new(e)

    # Adiciona Faces na malha
    bFaces = [(bVerts[i], bVerts[j], bVerts[k]) for (i,j,k) in lm.faces]
    for f in bFaces:
        bm.faces.new(f)

    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    # for f_idx in faces:
    #     bm.faces.new([bm.verts[i] for i in f_idx])

    bm.to_mesh(mesh)
    mesh.update()

    return mesh

    # add the mesh as an object into the scene with this utility module
    from bpy_extras import object_utils
    object_utils.object_data_add(context, mesh)
    # object_utils.object_data_add(context, mesh, operator=self)

