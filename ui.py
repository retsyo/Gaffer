# BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# END GPL LICENSE BLOCK #####

import bpy
from collections import OrderedDict
import bgl, blf
from math import pi, cos, sin, log
from mathutils import Vector, Matrix
from bpy_extras.view3d_utils import location_3d_to_region_2d
from bpy.app.handlers import persistent

from .constants import *
from .functions import *
from .operators import *


def draw_renderer_independant(gaf_props, row, light, users=[None, 1]):  # UI stuff that's shown for all renderers
    '''
        Parameters:
        users: a list, 0th position is data name, 1st position is number of users
    '''

    if "_Light:_(" + light.name + ")_" in gaf_props.MoreExpand and not gaf_props.MoreExpandAll:
        row.operator("gaffer.more_options_hide", icon='TRIA_DOWN', text='', emboss=False).light = light.name
    elif not gaf_props.MoreExpandAll:
        row.operator("gaffer.more_options_show", icon='TRIA_RIGHT', text='', emboss=False).light = light.name

    if gaf_props.SoloActive == '':
        if users[1] == 1:
            row.operator('gaffer.rename', text=light.name).light = light.name
        else:
            data_name = users[0][4:] if users[0].startswith('LAMP') else users[0][3:]
            op = row.operator('gaffer.rename', text='[' + str(users[1]) + '] ' + data_name)
            op.multiuser = users[0]
            op.light = data_name
            # if light.type == 'LAMP':
            #     op.multiuser = light.type
            #     op.light = light.data.name
            # else:
            #     op.light = light.name
    else:
        # Don't allow names to be edited during solo, will break the record of what was originally hidden
        row.label(text=light.name)

    visop = row.operator('gaffer.hide_light', text='', icon="%s" % 'RESTRICT_VIEW_ON' if light.hide else 'RESTRICT_VIEW_OFF', emboss=False)
    visop.light = light.name
    visop.dataname = users[0] if users[1] > 1 else "__SINGLE_USER__"
    visop.hide = not light.hide

    selop = row.operator("gaffer.select_light", icon="%s" % 'RESTRICT_SELECT_OFF' if light.select else 'SMALL_TRI_RIGHT_VEC', text="", emboss=False)
    selop.light = light.name
    selop.dataname = users[0] if users[1] > 1 else "__SINGLE_USER__"
    if gaf_props.SoloActive == '':
        solobtn = row.operator("gaffer.solo", icon='ZOOM_SELECTED', text='', emboss=False)
        solobtn.light = light.name
        solobtn.showhide = True
        solobtn.worldsolo = False
        solobtn.dataname = users[0] if users[1] > 1 else "__SINGLE_USER__"
    elif gaf_props.SoloActive == light.name:
        solobtn = row.operator("gaffer.solo", icon='ZOOM_PREVIOUS', text='', emboss=False)
        solobtn.light = light.name
        solobtn.showhide = False
        solobtn.worldsolo = False


def draw_BI_UI(context, layout, lights):
    maincol = layout.column(align=True)
    scene = context.scene
    gaf_props = scene.gaf_props

    lights_to_show = []
    # Check validity of list and make list of lights to display
    for light in lights:
        try:
            if light[0]:
                a = bpy.data.objects[light[0][1:-1]]  # will cause exception if obj no longer exists
                if (gaf_props.VisibleLightsOnly and not a.hide) or (not gaf_props.VisibleLightsOnly):
                    if (gaf_props.VisibleLayersOnly and isOnVisibleLayer(a, scene)) or (not gaf_props.VisibleLayersOnly):
                        if a.name not in [o.name for o in gaf_props.Blacklist]:
                            lights_to_show.append(light)
        except:
            box = maincol.box()
            row = box.row(align=True)
            row.label("Light list out of date")
            row.operator('gaffer.refresh_lights', icon='FILE_REFRESH', text='')

    # Don't show lights that share the same data
    duplicates = {}
    '''
    duplicates:
        A dict with the key: object type + data name (cannot use only the name in case of conflicts).
        The values are the number of duplicates for that key.
    '''
    templist = []
    for item in lights_to_show:
        light = scene.objects[item[0][1:-1]]  # drop the apostrophies
        if ('LAMP' + light.data.name) in duplicates:
            duplicates['LAMP' + light.data.name] += 1
        else:
            templist.append(item)
            duplicates['LAMP' + light.data.name] = 1
    lights_to_show = templist

    i = 0
    for item in lights_to_show:
        light = scene.objects[item[0][1:-1]]  # drop the apostrophies

        box = maincol.box()
        rowmain = box.row()
        split = rowmain.split()
        col = split.column()
        row = col.row(align=True)

        users = ['LAMP' + light.data.name, duplicates['LAMP' + light.data.name]]
        draw_renderer_independant(gaf_props, row, light, users)

        # strength
        row = col.row(align=True)
        row.prop(light.data, "type", text='', icon='LAMP_%s' % light.data.type, icon_only=True, emboss=False)
        row.separator()
        row.prop(light.data, 'energy', text="Strength")

        # color
        subcol = row.column(align=True)
        subrow = subcol.row(align=True)
        subrow.scale_x = 0.3
        subrow.prop(light.data, 'color', text='')

        # More Options
        if "_Light:_(" + light.name + ")_" in gaf_props.MoreExpand or gaf_props.MoreExpandAll:
            if light.data.type != 'HEMI':
                if light.data.type == 'AREA':
                    col = box.column()
                    if light.data.shape == 'RECTANGLE':
                        subcol = col.column(align=True)
                        row = subcol.row(align=True)
                        row.prop(light.data, "size", text="Size X")
                        row.prop(light.data, "shadow_ray_samples_x", text="Samples X")
                        row = subcol.row(align=True)
                        row.prop(light.data, "size_y", text="Size Y")
                        row.prop(light.data, "shadow_ray_samples_y", text="Samples Y")
                    else:
                        row = col.row(align=True)
                        row.prop(light.data, "size", text="Size")
                        row.prop(light.data, "shadow_ray_samples_x", text="Samples")
                elif light.data.type == 'SPOT':
                    col = box.column(align=True)
                    row = col.row(align=True)
                    row.prop(light.data, "spot_size", text='Spot Size')
                    row.prop(light.data, "spot_blend", text='Blend')
                    if light.data.shadow_method == 'RAY_SHADOW':
                        row = col.row(align=True)
                        row.prop(light.data, "shadow_soft_size", text="Size")
                        row.prop(light.data, "shadow_ray_samples", text="Samples")
                    col = box.column()
                else:
                    if light.data.shadow_method == 'RAY_SHADOW':
                        col = box.column()
                        row = col.row(align=True)
                        row.prop(light.data, "shadow_soft_size", text="Size")
                        row.prop(light.data, "shadow_ray_samples", text="Samples")

                col.prop(light.data, "shadow_method", text="")

                row = col.row(align=True)
                row.prop(light.data, "use_diffuse", toggle=True)
                row.prop(light.data, "use_specular", toggle=True)
            else:
                row = col.row(align=True)
                row.prop(light.data, "use_diffuse", toggle=True)
                row.prop(light.data, "use_specular", toggle=True)
            if light.data.type in ['SPOT', 'POINT']:
                col.prop(light.data, "falloff_type", text="Falloff")

    if len(lights_to_show) == 0:
        row = maincol.row()
        row.alignment = 'CENTER'
        row.label("No lights to show :)")

    # World
    if context.scene.world:
        world = context.scene.world
        box = layout.box()
        worldcol = box.column(align=True)
        col = worldcol.column(align=True)

        row = col.row(align=True)

        if "_Light:_(WorldEnviroLight)_" in gaf_props.MoreExpand and not gaf_props.MoreExpandAll:
            row.operator("gaffer.more_options_hide", icon='TRIA_DOWN', text='', emboss=False).light = "WorldEnviroLight"
        elif not gaf_props.MoreExpandAll:
            row.operator("gaffer.more_options_show", icon='TRIA_RIGHT', text='', emboss=False).light = "WorldEnviroLight"

        row.label(text="World")
        if gaf_props.SoloActive == '':
            solobtn = row.operator("gaffer.solo", icon='ZOOM_SELECTED', text='', emboss=False)
            solobtn.light = "WorldEnviroLight"
            solobtn.showhide = True
            solobtn.worldsolo = True
        elif gaf_props.SoloActive == "WorldEnviroLight":
            solobtn = row.operator("gaffer.solo", icon='ZOOM_PREVIOUS', text='', emboss=False)
            solobtn.light = "WorldEnviroLight"
            solobtn.showhide = False
            solobtn.worldsolo = True

        col = worldcol.column()
        row = col.row(align=True)

        row.label(text="", icon='WORLD')
        row.separator()

        row.prop(world, 'horizon_color', text='')
        if world.use_sky_blend:
            row.prop(world, 'zenith_color', text='')

        if "_Light:_(WorldEnviroLight)_" in gaf_props.MoreExpand or gaf_props.MoreExpandAll:
            col = worldcol.column()
            row = col.row(align=True)
            row.prop(world, 'use_sky_blend')
            if world.use_sky_blend:
                row.prop(world, 'use_sky_paper', text="Paper", toggle=True)
                row.prop(world, 'use_sky_real', text="Real", toggle=True)

            row = col.row(align=True)
            row.prop(world.light_settings, "use_ambient_occlusion", text="Ambient Occlusion")
            if world.light_settings.use_ambient_occlusion:
                row.prop(world.light_settings, "ao_blend_type", text="")
            if world.light_settings.use_ambient_occlusion:
                row = col.row(align=True)
                row.prop(world.light_settings, "ao_factor")
                row.prop(world.light_settings, "distance")

            col.prop(world.light_settings, "use_environment_light", text="Environment Lighting")
            if world.light_settings.use_environment_light:
                col.prop(world.light_settings, "environment_energy", text='Energy')

            if world.light_settings.use_environment_light or world.light_settings.use_ambient_occlusion:
                if world.light_settings.gather_method == 'APPROXIMATE':
                    col.prop(world.light_settings, "use_indirect_light", text="Indirect Lighting")
                    if world.light_settings.use_indirect_light:
                        row = col.row(align=True)
                        row.prop(world.light_settings, "indirect_factor")
                        row.prop(world.light_settings, "indirect_bounces")

                worldcol.separator()
                col = worldcol.column(align=True)
                row = col.row(align=True)
                row.prop(world.light_settings, "gather_method", expand=True)

                if world.light_settings.gather_method == 'APPROXIMATE':
                    col.prop(world.light_settings, "passes")
                    col.prop(world.light_settings, "error_threshold")
                    col.prop(world.light_settings, "correction")
                else:
                    col.prop(world.light_settings, "samples")


def draw_cycles_UI(context, layout, lights):
    maincol = layout.column(align=False)
    scene = context.scene
    gaf_props = scene.gaf_props

    lights_to_show = []
    # Check validity of list and make list of lights to display
    for light in lights:
        try:
            if light[0]:
                a = bpy.data.objects[light[0][1:-1]]  # will cause exception if obj no longer exists
                if (gaf_props.VisibleLightsOnly and not a.hide) or (not gaf_props.VisibleLightsOnly):
                    if a.type != 'LAMP':
                        b = bpy.data.materials[light[1][1:-1]]
                        if b.use_nodes:
                            c = b.node_tree.nodes[light[2][1:-1]]
                    else:
                        if a.data.use_nodes:
                            c = a.data.node_tree.nodes[light[2][1:-1]]
                    if (gaf_props.VisibleLayersOnly and isOnVisibleLayer(a, scene)) or (not gaf_props.VisibleLayersOnly):
                        if a.name not in [o.name for o in gaf_props.Blacklist]:
                            lights_to_show.append(light)
        except:
            box = maincol.box()
            row = box.row(align=True)
            row.label("Light list out of date")
            row.operator('gaffer.refresh_lights', icon='FILE_REFRESH', text='')

    # Don't show lights that share the same data
    duplicates = {}
    '''
    duplicates:
        A dict with the key: object type + data name (cannot use only the name in case of conflicts).
        The values are the number of duplicates for that key.
    '''
    templist = []
    for item in lights_to_show:
        light = scene.objects[item[0][1:-1]]  # drop the apostrophies
        if light.type == 'LAMP':
            if ('LAMP' + light.data.name) in duplicates:
                duplicates['LAMP' + light.data.name] += 1
            else:
                templist.append(item)
                duplicates['LAMP' + light.data.name] = 1
        else:
            mat = bpy.data.materials[item[1][1:-1]]
            if ('MAT' + mat.name) in duplicates:
                duplicates['MAT' + mat.name] += 1
            else:
                templist.append(item)
                duplicates['MAT' + mat.name] = 1
    lights_to_show = templist

    i = 0
    for item in lights_to_show:
        light = scene.objects[item[0][1:-1]]  # drop the apostrophies
        doesnt_use_nodes = False
        is_portal = False
        if light.type == 'LAMP':
            material = None
            if light.data.use_nodes:
                node_strength = light.data.node_tree.nodes[item[2][1:-1]]
            else:
                doesnt_use_nodes = True

            if light.data.type == 'AREA' and light.data.cycles.is_portal:
                is_portal = True
        else:
            material = bpy.data.materials[item[1][1:-1]]
            if material.use_nodes:
                node_strength = material.node_tree.nodes[item[2][1:-1]]
            else:
                doesnt_use_nodes = True

        if doesnt_use_nodes:
            box = maincol.box()
            row = box.row()
            row.label("\"" + light.name + "\" doesn't use nodes!")
            if light.type == 'LAMP':
                row.operator('gaffer.lamp_use_nodes', icon='NODETREE', text='').light = light.name
        else:
            if item[3].startswith("'"):
                socket_strength_str = str(item[3][1:-1])
            else:
                socket_strength_str = str(item[3])

            if socket_strength_str.startswith('o'):
                socket_strength_type = 'o'
                socket_strength = int(socket_strength_str[1:])
            elif socket_strength_str.startswith('i'):
                socket_strength_type = 'i'
                socket_strength = int(socket_strength_str[1:])
            else:
                socket_strength_type = 'i'
                socket_strength = int(socket_strength_str)

            box = maincol.box()
            rowmain = box.row()
            split = rowmain.split()
            col = split.column()
            row = col.row(align=True)

            if light.type == 'LAMP':
                users = ['LAMP' + light.data.name, duplicates['LAMP' + light.data.name]]
            else:
                users = ['MAT' + material.name, duplicates['MAT' + material.name]]
            draw_renderer_independant(gaf_props, row, light, users)

            # strength
            if not is_portal:
                row = col.row(align=True)
                strength_sockets = node_strength.inputs
                if socket_strength_type == 'o':
                    strength_sockets = node_strength.outputs
                if light.type == 'LAMP':
                    row.prop(light.data, "type", text='', icon='LAMP_%s' % light.data.type, icon_only=True, emboss=False)
                else:
                    row.label(text='', icon='MESH_GRID')

                row.separator()
                try:
                    if ((socket_strength_type == 'i' and not strength_sockets[socket_strength].is_linked) \
                    or (socket_strength_type == 'o' and strength_sockets[socket_strength].is_linked)) \
                    and hasattr(strength_sockets[socket_strength], "default_value"):
                        row.prop(strength_sockets[socket_strength], 'default_value', text='Strength')
                    else:
                        row.label("  Node Invalid")
                except:
                    row.label("  Node Invalid")

                # color
                if light.type == 'LAMP':
                    nodes = light.data.node_tree.nodes
                else:
                    nodes = material.node_tree.nodes
                socket_color = 0
                node_color = None
                emissions = []  # make a list of all linked Emission shaders, use the right-most one
                for node in nodes:
                    if node.type == 'EMISSION':
                        if node.outputs[0].is_linked:
                            emissions.append(node)
                if emissions:
                    node_color = sorted(emissions, key=lambda x: x.location.x, reverse=True)[0]

                    if not node_color.inputs[socket_color].is_linked:
                        subcol = row.column(align=True)
                        subrow = subcol.row(align=True)
                        subrow.scale_x = 0.3
                        subrow.prop(node_color.inputs[socket_color], 'default_value', text='')
                    else:
                        from_node = node_color.inputs[socket_color].links[0].from_node
                        if from_node.type == 'RGB':
                            subcol = row.column(align=True)
                            subrow = subcol.row(align=True)
                            subrow.scale_x = 0.3
                            subrow.prop(from_node.outputs[0], 'default_value', text='')
                        elif from_node.type == 'TEX_IMAGE' or from_node.type == 'TEX_ENVIRONMENT':
                            row.prop(from_node, 'image', text='')
                        elif from_node.type == 'BLACKBODY':
                            row.prop(from_node.inputs[0], 'default_value', text='Temperature')
                            if gaf_props.ColTempExpand and gaf_props.LightUIIndex == i:
                                row.operator('gaffer.col_temp_hide', text='', icon='MOVE_UP_VEC')
                                col = col.column(align=True)
                                col.separator()
                                col.label("Color Temperature Presets:")
                                ordered_col_temps = OrderedDict(sorted(col_temp.items()))
                                for temp in ordered_col_temps:
                                    op = col.operator('gaffer.col_temp_preset', text=temp[3:], icon='COLOR')  # temp[3:] removes number used for ordering
                                    op.temperature = temp
                                    op.light = light.name
                                    if material:
                                        op.material = material.name
                                    if node_color:
                                        op.node = node_color.name
                                col.separator()
                            else:
                                row.operator('gaffer.col_temp_show', text='', icon='COLOR').l_index = i
                        elif from_node.type == 'WAVELENGTH':
                            row.prop(from_node.inputs[0], 'default_value', text='Wavelength')

            # More Options
            if "_Light:_(" + light.name + ")_" in gaf_props.MoreExpand or gaf_props.MoreExpandAll:
                col = box.column()
                row = col.row(align=True)
                if light.type == 'LAMP':
                    if light.data.type == 'AREA':
                        if light.data.shape == 'RECTANGLE':
                            row.prop(light.data, 'size')
                            row.prop(light.data, 'size_y')
                            row = col.row(align=True)
                        else:
                            row.prop(light.data, 'size')
                    else:
                        row.prop(light.data, 'shadow_soft_size', text='Size')

                    if scene.cycles.progressive == 'BRANCHED_PATH':
                        row.prop(light.data.cycles, "samples")

                    if not is_portal:
                        row = col.row(align=True)
                        row.prop(light.data.cycles, "use_multiple_importance_sampling", text='MIS', toggle=True)
                        row.prop(light.data.cycles, "cast_shadow", text='Shadows', toggle=True)
                        row.separator()
                        row.prop(light.cycles_visibility, "diffuse", text='Diff', toggle=True)
                        row.prop(light.cycles_visibility, "glossy", text='Spec', toggle=True)

                    if light.data.type == 'SPOT':
                        row = col.row(align=True)
                        row.prop(light.data, "spot_size", text='Spot Size')
                        row.prop(light.data, "spot_blend", text='Blend')

                else:  # MESH light
                    row.prop(material.cycles, "sample_as_light", text='MIS', toggle=True)
                    row.separator()
                    row.prop(light.cycles_visibility, "camera", text='Cam', toggle=True)
                    row.prop(light.cycles_visibility, "diffuse", text='Diff', toggle=True)
                    row.prop(light.cycles_visibility, "glossy", text='Spec', toggle=True)
                if hasattr(light, "GafferFalloff"):
                    drawfalloff = True
                    if light.type == 'LAMP':
                        if light.data.type == 'SUN' or light.data.type == 'HEMI' or (light.data.type == 'AREA' and light.data.cycles.is_portal):
                            drawfalloff = False
                    if drawfalloff:
                        col.prop(light, "GafferFalloff", text="Falloff")
                        if node_strength.type != 'LIGHT_FALLOFF' and light.GafferFalloff != 'quadratic':
                            col.label("Light Falloff node is missing", icon="ERROR")
                if light.type == 'LAMP':
                    if light.data.type == 'AREA':
                        col.prop(light.data.cycles, 'is_portal', "Portal")
            i += 1

    if len(lights_to_show) == 0:
        row = maincol.row()
        row.alignment = 'CENTER'
        row.label("No lights to show :)")

    # World
    if context.scene.world:
        world = context.scene.world
        box = layout.box()
        worldcol = box.column(align=True)
        col = worldcol.column(align=True)

        row = col.row(align=True)

        if "_Light:_(WorldEnviroLight)_" in gaf_props.MoreExpand and not gaf_props.MoreExpandAll:
            row.operator("gaffer.more_options_hide", icon='TRIA_DOWN', text='', emboss=False).light = "WorldEnviroLight"
        elif not gaf_props.MoreExpandAll:
            row.operator("gaffer.more_options_show", icon='TRIA_RIGHT', text='', emboss=False).light = "WorldEnviroLight"

        row.label(text="World")
        row.prop(gaf_props, "WorldVis", text="", icon='%s' % 'RESTRICT_VIEW_OFF' if gaf_props.WorldVis else 'RESTRICT_VIEW_ON', emboss=False)

        if gaf_props.SoloActive == '':
            solobtn = row.operator("gaffer.solo", icon='ZOOM_SELECTED', text='', emboss=False)
            solobtn.light = "WorldEnviroLight"
            solobtn.showhide = True
            solobtn.worldsolo = True
        elif gaf_props.SoloActive == "WorldEnviroLight":
            solobtn = row.operator("gaffer.solo", icon='ZOOM_PREVIOUS', text='', emboss=False)
            solobtn.light = "WorldEnviroLight"
            solobtn.showhide = False
            solobtn.worldsolo = True

        col = worldcol.column()
        row = col.row(align=True)

        row.label(text="", icon='WORLD')
        row.separator()

        color_node = None
        if world.use_nodes:
            backgrounds = []  # make a list of all linked Background shaders, use the right-most one
            background = None
            for node in world.node_tree.nodes:
                if node.type == 'BACKGROUND':
                    if node.outputs[0].is_linked:
                        backgrounds.append(node)
            if backgrounds:
                background = sorted(backgrounds, key=lambda x: x.location.x, reverse=True)[0]
                # Strength
                if background.inputs[1].is_linked:
                    strength_node = None
                    current_node = background.inputs[1].links[0].from_node
                    temp_current_node = None
                    i = 0  # Failsafe in case of infinite loop (which can happen from accidental cyclic links)
                    while strength_node == None and i < 100:  # limitted to 100 chained nodes
                        i += 1
                        connected_inputs = False
                        if temp_current_node:
                            current_node = temp_current_node
                        for socket in current_node.inputs:
                            # stop at first node with an unconnected Value socket
                            if socket.type == 'VALUE' and not socket.is_linked:
                                strength_node = current_node
                            else:
                                if socket.is_linked:
                                    temp_current_node = socket.links[0].from_node

                    if strength_node:
                        for socket in strength_node.inputs:
                            if socket.type == 'VALUE' and not socket.is_linked:  # use first color socket
                                row.prop(socket, 'default_value', text="Strength")
                                break
                else:
                    row.prop(background.inputs[1], "default_value", text="Strength")

                # Color
                if background.inputs[0].is_linked:
                    current_node = background.inputs[0].links[0].from_node
                    i = 0  # Failsafe in case of infinite loop (which can happen from accidental cyclic links)
                    while color_node == None and i < 100:  # limitted to 100 chained nodes
                        i += 1
                        connected_inputs = False
                        for socket in current_node.inputs:
                            # stop at node end of chain, or node with only vector inputs:
                            if socket.type != 'VECTOR' and socket.is_linked:
                                connected_inputs = True
                                current_node = socket.links[0].from_node
                        if not connected_inputs:
                            color_node = current_node

                    if color_node.type == 'TEX_IMAGE' or color_node.type == 'TEX_ENVIRONMENT':
                        row.prop(color_node, 'image', text='')
                    elif color_node.type == 'TEX_SKY':
                        row.prop(color_node, 'sun_direction', text='')
                    else:
                        if color_node.inputs:
                            for socket in color_node.inputs:
                                if socket.type == 'RGBA':  # use first color socket
                                    row.prop(socket, 'default_value', text='')
                                    break
                else:
                    row.prop(background.inputs[0], "default_value", text="")
            else:
                row.label("No node found!")
        else:
            row.prop(world, 'horizon_color', text='')

        # Extra
        if "_Light:_(WorldEnviroLight)_" in gaf_props.MoreExpand or gaf_props.MoreExpandAll:
            worldcol.separator()
            col = worldcol.column()
            row = col.row()
            row.prop(world.cycles, "sample_as_light", text="MIS", toggle=True)
            row.prop(gaf_props, "WorldReflOnly", text="Refl Only")
            if world.cycles.sample_as_light:
                col = worldcol.column()
                row = col.row(align=True)
                row.prop(world.cycles, "sample_map_resolution", text="MIS res")
                if scene.cycles.progressive == 'BRANCHED_PATH':
                    row.prop(world.cycles, "samples", text="Samples")
            worldcol.separator()
            col = worldcol.column(align=True)
            col.prop(world.light_settings, "use_ambient_occlusion", text="Ambient Occlusion")
            if world.light_settings.use_ambient_occlusion:
                row = col.row(align=True)
                row.prop(world.light_settings, "ao_factor")
                row.prop(world.light_settings, "distance")

            if color_node:
                if color_node.type == 'TEX_SKY':
                    if world.node_tree and world.use_nodes:
                        col = worldcol.column(align = True)
                        row = col.row(align = True)
                        if gaf_props.SunObject:
                            row.operator('gaffer.link_sky_to_sun', icon="LAMP_SUN").node_name = color_node.name
                        else:
                            row.label("Link Sky Texture:")
                        row.prop_search(gaf_props, "SunObject", bpy.data, "objects", text="")


class GafferPanelLights(bpy.types.Panel):

    bl_label = "Lights"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Gaffer"

    @classmethod
    def poll(cls, context):
        return True if context.scene.render.engine in supported_renderers else False

    def draw(self, context):
        scene = context.scene
        gaf_props = scene.gaf_props
        lights_str = gaf_props.Lights
        lights = stringToNestedList(lights_str)
        layout = self.layout

        col = layout.column(align=True)
        row = col.row(align=True)
        if gaf_props.SoloActive != "":  # if in solo mode
            solobtn = row.operator("gaffer.solo", icon='ZOOM_PREVIOUS', text='')
            solobtn.light = "None"
            solobtn.showhide = False
            solobtn.worldsolo = False
        row.operator('gaffer.refresh_lights', text="Refresh", icon='FILE_REFRESH')  # may not be needed if drawing errors are cought correctly (eg newly added lights)
        row.prop(gaf_props, "VisibleLayersOnly", text='', icon='LAYER_ACTIVE')
        row.prop(gaf_props, "VisibleLightsOnly", text='', icon='VISIBLE_IPO_ON')
        row.prop(gaf_props, "MoreExpandAll", text='', icon='PREFERENCES')

        if gaf_props.SoloActive != '':
            try:
                o = bpy.data.objects[gaf_props.SoloActive]  # Will cause exception if object by that name doesn't exist
            except:
                if gaf_props.SoloActive != "WorldEnviroLight":
                    # In case solo'd light changes name, theres no other way to exit solo mode
                    col.separator()
                    row = col.row()
                    row.label("       ")
                    solobtn = row.operator("gaffer.solo", icon='ZOOM_PREVIOUS', text='Reset Solo')
                    solobtn.showhide = False
                    row.label("       ")

        if scene.render.engine == 'BLENDER_RENDER':
            draw_BI_UI(context, layout, lights)
        elif scene.render.engine == 'CYCLES':
            draw_cycles_UI(context, layout, lights)
        else:
            layout.label ("Render Engine not supported!")


class GafferPanelTools(bpy.types.Panel):

    bl_label = "Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Gaffer"

    @classmethod
    def poll(cls, context):
        return True if context.scene.render.engine in supported_renderers else False

    def draw(self, context):
        scene = context.scene
        gaf_props = scene.gaf_props
        layout = self.layout

        maincol = layout.column()

        # Aiming
        col = maincol.column(align = True)
        col.label("Aim:", icon='MAN_TRANS')
        col.operator('gaffer.aim', text="Selection at 3D cursor").target_type = 'CURSOR'
        col.operator('gaffer.aim', text="Selected at active").target_type = 'ACTIVE'
        col.operator('gaffer.aim', text="Active at selected").target_type = 'SELECTED'

        maincol.separator()

        # Draw Radius
        box = maincol.box() if gaf_props.IsShowingRadius else maincol.column()
        sub = box.column(align=True)
        row = sub.row(align=True)
        row.operator('gaffer.show_radius', text="Show Radius" if not gaf_props.IsShowingRadius else "Hide Radius", icon='META_EMPTY')
        if gaf_props.IsShowingRadius:
            row.operator('gaffer.refresh_bgl', text="", icon="FILE_REFRESH")
            sub.prop(gaf_props, 'LightRadiusAlpha', slider=True)
            row = sub.row(align=True)
            row.active = gaf_props.IsShowingRadius
            row.prop(gaf_props, 'LightRadiusDrawType', text="")
            row.prop(gaf_props, 'LightRadiusUseColor')
            row = sub.row(align=True)
            row.active = gaf_props.IsShowingRadius
            row.prop(gaf_props, 'LightRadiusXray')
            row.prop(gaf_props, 'LightRadiusSelectedOnly')
            row = sub.row(align=True)
            row.prop(gaf_props, 'DefaultRadiusColor')

        maincol.separator()

        # Draw Label
        box = maincol.box() if gaf_props.IsShowingLabel else maincol.column()
        sub = box.column(align=True)
        row = sub.row(align=True)
        row.operator('gaffer.show_label', text="Show Label" if not gaf_props.IsShowingLabel else "Hide Label", icon='LONGDISPLAY')
        if gaf_props.IsShowingLabel:
            row.operator('gaffer.refresh_bgl', text="", icon="FILE_REFRESH")
            label_draw_type = gaf_props.LabelDrawType
            sub.prop(gaf_props, 'LabelAlpha', slider=True)
            sub.prop(gaf_props, 'LabelFontSize')
            row = sub.row(align=True)
            row.prop(gaf_props, 'LabelDrawType', text='')
            row.prop(gaf_props, 'LabelUseColor')
            if label_draw_type == 'color_bg' or not gaf_props.LabelUseColor:
                row = sub.row(align=True)
                row.prop(gaf_props, 'LabelTextColor')
            if label_draw_type == 'plain_bg' or (not gaf_props.LabelUseColor and label_draw_type != 'color_text'):
                row = sub.row(align=True)
                row.prop(gaf_props, 'DefaultLabelBGColor')
            row = sub.row(align=True)
            row.prop(gaf_props, 'LabelAlign', text="")
            if gaf_props.LabelAlign != 'c':
                row.prop(gaf_props, 'LabelMargin')

        maincol.separator()

        # Blacklist
        box = maincol.box()
        sub = box.column(align=True)
        sub.label('Blacklist:')
        if gaf_props.Blacklist:
            sub.template_list("OBJECT_UL_object_list", "", gaf_props, "Blacklist", gaf_props, "BlacklistIndex", rows=2)
        row = sub.row(align=True)
        row.operator('gaffer.blacklist_add', icon='ZOOMIN')
        row.operator('gaffer.blacklist_remove', icon='ZOOMOUT')


class OBJECT_UL_object_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        obj = item
        layout.prop(obj, 'name', text="", emboss=False)
        

def gaffer_node_menu_func(self, context):
    if context.space_data.node_tree.type == 'SHADER' and context.space_data.shader_type == 'OBJECT':
        light_dict = dictOfLights()
        if context.object.name in light_dict:
            layout = self.layout
            layout.operator('gaffer.node_set_strength')