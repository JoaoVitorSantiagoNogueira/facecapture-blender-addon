import bpy
import numpy


def main(context):
    for ob in context.scene.objects:
        print(ob)

def get_vals (obj):
    #source_obj = bpy.data.objects.get("origem.001")
    #target_obj = bpy.data.objects.get("Cube.004")
    
    shape_keys = obj.data.shape_keys.key_blocks
    #shape_keys_target = target_obj.data.shape_keys.key_blocks
        
    values = numpy.fromiter((sks.value for sks in shape_keys), float)
    names  = (sks.name for sks in shape_keys)

    source = tuple(zip(names, values)) 
    return source

def calculate_shape_key_weights (target, source = {}, simpified = True):
    # source and target are both 1d collum arrays
    # we want to find and a, so that Source * a = Target
    # Source cannot be inverted, so we must solve a system
    if (simpified):
        # if source contains only a single non-zero digit,
        # we know it`s correspondent collum must be the values of target divided by the value of source
        # hence, we'll create a 1d array, for the line we'll replace in the final matrix. 
        pos = next((i for i, x in enumerate(source) if x!= 0), None) #find the position of first non zero element.
        return (target/source[pos]), pos 
    return #numpy.dot(source.transpose(),target.transpose())

class Blendshape_retarget_manual(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "retarget.blendshapes_all"
    bl_label = "Retarget each blendshape operator"

    def execute(self, context):
        fc = context.scene.fc_settings
        source_mesh = fc.blendshape_mesh
        target_mesh = fc.retarget_mesh

        s = get_vals (source_mesh)
        t = get_vals (target_mesh)

        calculate_shape_key_weights(s,t)
        return {'FINISHED'}

class Blendshape_retarget_single_blendshape(bpy.types.Operator):
    """Stores values used in the conversion between the two shape key meshes"""
    bl_idname = "retarget.blendshapes_single"
    bl_label = "Calculate Conversion Values"

    def execute(self, context):
        #select the relevant blendshape information from the target retarget mesh
        fc = context.scene.fc_settings


        target_mesh = fc.retarget_mesh      # the mesh we'll extract or target values
        source_mesh = fc.blendshape_mesh    # the mesh we'll save our information onto
        target_sk   = fc.retarget_shape_key # name of the shape key we want to use as reference


        # since we are operating with a single blend shape we can just all values of our target with the value of our source
        divider = source_mesh.data.shape_keys.key_blocks[target_sk].value
        if (divider == 0):               #but we can't divide by zero, so in that case we asume it to be 1
            divider = 1


        organized = get_vals (target_mesh)  # this organizes the complex shape keys into simple touples of values and names

        #make sure our target shape key atrribute exists so we store our custom properties
        if target_sk not in source_mesh.data.shape_keys:
            source_mesh.data.shape_keys[target_sk] ={}

        #load all values into the final refence structure, for source shape key, pairing with every target shape key r[0], we'll atribute their value r[1]
        for o in organized:
            source_mesh.data.shape_keys[target_sk][o[0]] = o[1]/divider

        return {'FINISHED'}

class Blendshape_target_update(bpy.types.Operator):
    """Set new shape key weights to match meshes"""
    bl_idname = "retarget.blendshapes_update"
    bl_label = "Apply changes to the final model"

    def execute(self, context):
        #select the relevant blendshape information from the retarget and blendshape mesh
        fc = context.scene.fc_settings
        t = fc.retarget_mesh.data.shape_keys.key_blocks
        s = fc.blendshape_mesh.data.shape_keys.key_blocks
        conversion = fc.blendshape_mesh.data.shape_keys

        ###clear final blendshape values
        for i in t:
            i.value = 0

        for i in s:
            if i.name in conversion: 
                for j in t:
                    if j.name in conversion[i.name]:
                        j.value += i.value * conversion[i.name][j.name]

        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(Blendshape_retarget_manual.bl_idname, text=Blendshape_retarget_manual.bl_label)

# Register and add to the "object" menu (required to also use F3 search "Simple Object Operator" for quick access)
def register():
    bpy.utils.register_class(Blendshape_retarget_manual)
    bpy.utils.register_class(Blendshape_retarget_single_blendshape)
    bpy.utils.register_class(Blendshape_target_update)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(Blendshape_target_update)
    bpy.utils.unregister_class(Blendshape_retarget_single_blendshape)
    bpy.utils.unregister_class(Blendshape_retarget_manual)
    bpy.types.VIEW3D_MT_object.remove(menu_func)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.object.simple_operator()
