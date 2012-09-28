#!/usr/bin/env python

from gimpfu import *
import re
import math

COPYRIGHT1 = "Nephi Johnson"
COPYRIGHT2 = "Nephi Johnson"
COPYRIGHT_YEAR = "2012"



def make_frame_name(frame_num):
	return "Frame %d" % (frame_num) 

def _shift_frames_helper(img, start_frame_num, delta):
	for frame in get_frames(img):
		curr_frame_num = get_frame_num(frame)
		if curr_frame_num >= start_frame_num:
			frame.name = make_frame_name(curr_frame_num+delta) + " SHIFTTMP"

	for frame in get_frames(img):
		frame.name = frame.name.replace(" SHIFTTMP", "")

def shift_frames_up(img, start_frame_num):
	"""
	Shift frames "up" - number-wise a frame would go from
	being frame 4 to frame 3
	"""
	_shift_frames_helper(img, start_frame_num, -1)

def shift_frames_down(img, start_frame_num):
	"""
	Shift frames "down" - number-wise a frame would go from
	being frame 3 to frame 4
	"""
	_shift_frames_helper(img, start_frame_num, 1)

def get_frames(img):
	res = []
	for layer in img.layers:
		if get_frame_num(layer) is not None:
			res.append(layer)
	return res

def goto_frame(img, frame_num):
	"""
	Sets the desired frame folder to be visible and all
	other frame folders to not be visible.

	@returns whether or not it even found the frame you were
	looking for
	"""
	found_frame = False
	for frame in get_frames(img):
		curr_frame_num = get_frame_num(frame)
		if curr_frame_num == frame_num:
			frame.visible = True
			found_frame = True
			if len(frame.children) > 0:
				pdb.gimp_image_set_active_layer(img, frame.children[0])
			else:
				pdb.gimp_image_set_active_layer(img, frame)
		else:
			frame.visible = False

	return found_frame

def get_last_frame_position(img):
	last_pos = -1
	curr_pos = 0
	for layer in img.layers:
		curr_frame_num = get_frame_num(layer)
		if curr_frame_num is not None:
			last_pos = pdb.gimp_image_get_layer_position(img, layer)

	return last_pos

def get_last_frame_num(img):
	max_frame_num = -1
	for layer in img.layers:
		curr_frame_num = get_frame_num(layer)
		if curr_frame_num is not None:
			if curr_frame_num > max_frame_num:
				max_frame_num = curr_frame_num

	return max_frame_num

def get_frame_root(layer):
	"""
	Assumes the layer is either a valid layer inside of a frame
	folder, or that it's a frame folder itself
	"""
	if pdb.gimp_item_is_group(layer):
		return layer
	
	return layer.parent

def get_frame_num(layer):
	if layer is None:
		return None

	match_string = None

	# it's a folder, so match off the folder's name
	if pdb.gimp_item_is_group(layer):
		# all frame folders must be at top level
		# (arbitrary, I know, but oh well)
		if layer.parent is not None:
			return None

		match_string = layer.name

	# it's a normal layer (not a folder), so check
	# to see if it's in a frame folder
	else:
		if layer.parent is None:
			return None
		if not pdb.gimp_item_is_group(layer.parent):
			return None

		match_string = layer.parent.name
	
	match = re.match(r"Frame (\d+)", match_string)

	if match is None:
		return None

	frame = int(match.groups()[0])
	return frame

def get_layers_in_frame(img, frame_num):
	res = []

	for layer in img.layers:
		layer_frame_num = get_frame_num(layer.name)
		if layer_frame_num == frame_num:
			res.append(layer)
	
	return res

# -----------------------------------------------
# -----------------------------------------------
# -----------------------------------------------

def narly_sprite_export_flatten(img, layer, reverse):
	new_img = gimp.Image(img.width, img.height, img.base_type)
	gimp.Display(new_img)
	gimp.displays_flush()

	frames = get_frames(img)

	if reverse:
		frames.reverse()

	for frame in frames:
		frame_num = get_frame_num(frame)
		goto_frame(img, frame_num)
		pdb.gimp_edit_copy_visible(img)
		new_layer = pdb.gimp_layer_new(
			new_img,
			new_img.width,
			new_img.height,
			new_img.base_type*2+1,
			make_frame_name(frame_num),
			100,	# opacity
			NORMAL_MODE
		)
		pdb.gimp_image_insert_layer(new_img, new_layer, None, len(new_img.layers))
		pasted_layer = pdb.gimp_edit_paste(new_layer, 0) # 0 = clear selection in the new image
		pdb.gimp_floating_sel_anchor(pasted_layer)
	
	return new_img

register(
	"python_fu_narly_sprite_convert_frames_to_layers",	# unique name for plugin
	"Narly Sprite Export Flatten",		# short name
	"Flatten all of the frames into individual layers",	# long name
	COPYRIGHT1,
	COPYRIGHT2,
	COPYRIGHT_YEAR,	# copyright year
	"<Image>/Sprite/Export/Flatten",	# what to call it in the menu
	"*",	# used when creating a new image (blank), else, use "*" for all existing image types
	[
		(PF_TOGGLE, "reverse", "Reverse Frame Order", False)
	],	# input params,
	[],	# output params,
	narly_sprite_export_flatten	# actual function
)

# -----------------------------------------------
# -----------------------------------------------
# -----------------------------------------------

def narly_sprite_copy_layer_to_all_frames(img, layer):
	"""
	Copies the current layer to all frames. If the current layer is in a
	frame, it will try to copy it to the same position. Otherwise, it
	is added at the last position.
	"""
	dont_copy_to = get_frame_num(layer)
	frame_pos = -1
	if dont_copy_to is not None:
		frame_pos = pdb.gimp_image_get_layer_position(img, layer)

	pdb.gimp_undo_push_group_start(img)

	for frame in get_frames(img):
		frame_num = get_frame_num(frame)
		if frame_num == dont_copy_to:
			continue
		copied_layer = layer.copy()
		copied_layer.name = layer.name
		pos_to_insert_at = frame_pos if frame_pos != -1 else len(frame.children)
		pdb.gimp_image_insert_layer(img, copied_layer, frame, pos_to_insert_at)
	
	# restore focus back to the original layer
	pdb.gimp_image_set_active_layer(img, layer)

	pdb.gimp_undo_push_group_end(img)

register(
	"python_fu_narly_sprite_copy_layer_to_all_frames",	# unique name for plugin
	"Narly Sprite Copy Layer to All Frames",		# short name
	"Narly Sprite Copy Layer to All Frames",	# long name
	COPYRIGHT1,
	COPYRIGHT2,
	COPYRIGHT_YEAR,	# copyright year
	"<Image>/Sprite/Layer to all Frames",	# what to call it in the menu
	"*",	# used when creating a new image (blank), else, use "*" for all existing image types
	[
	],	# input params,
	[],	# output params,
	narly_sprite_copy_layer_to_all_frames	# actual function
)


# -----------------------------------------------
# -----------------------------------------------
# -----------------------------------------------

HORIZONTAL = 0
GRID = 1
def narly_sprite_export_sprite_sheet(img, layer, sheet_type):
	frames = get_frames(img)

	if sheet_type == HORIZONTAL:
		new_img = gimp.Image(img.width * len(frames), img.height, img.base_type)
		gimp.Display(new_img)
		gimp.displays_flush()

		for frame in get_frames(img):
			frame_num = get_frame_num(frame)
			goto_frame(img, frame_num)
			pdb.gimp_edit_copy_visible(img)
			new_layer = pdb.gimp_layer_new(
				new_img,
				img.width,
				img.height,
				new_img.base_type*2+1,
				make_frame_name(frame_num),
				100,	# opacity
				NORMAL_MODE
			)
			pdb.gimp_image_insert_layer(new_img, new_layer, None, len(new_img.layers))
			pasted_layer = pdb.gimp_edit_paste(new_layer, 0) # 0 = clear selection in the new image
			pdb.gimp_floating_sel_anchor(pasted_layer)

			pdb.gimp_layer_set_offsets(new_layer, frame_num*img.width, 0)
	
	elif sheet_type == GRID:
		# determine the total number of rows and columns in the sprite sheet
		total_area = img.width * img.height * len(frames)
		square = math.sqrt(total_area)
		num_rows = square / img.height
		num_cols = square / img.width

		ceil_rows = math.ceil(num_rows) * img.height * img.width * math.floor(num_cols)
		ceil_cols = math.floor(num_rows) * img.height * img.width * math.ceil(num_cols)
		both_ceil = math.ceil(num_rows) * img.height * img.width * math.ceil(num_cols)

		if ceil_rows >= total_area and ceil_cols >= total_area:
			if ceil_rows < ceil_cols:
				num_rows = math.ceil(num_rows)
				num_cols = math.floor(num_cols)
			else:
				num_rows = math.floor(num_rows)
				num_cols = math.ceil(num_cols)
		if ceil_rows >= total_area:
			num_rows = math.ceil(num_rows)
			num_cols = math.floor(num_cols)
		if ceil_cols >= total_area:
			num_rows = math.floor(num_rows)
			num_cols = math.ceil(num_cols)
		elif both_ceil >= total_area:
			num_rows = math.ceil(num_rows)
			num_cols = math.ceil(num_cols)

		num_cols = int(num_cols)
		num_rows = int(num_rows)

		new_img = gimp.Image(img.width*num_cols, img.height*num_rows, img.base_type)
		gimp.Display(new_img)
		gimp.displays_flush()

		for frame in get_frames(img):
			frame_num = get_frame_num(frame)

			goto_frame(img, frame_num)
			pdb.gimp_edit_copy_visible(img)
			new_layer = pdb.gimp_layer_new(
				new_img,
				img.width,
				img.height,
				new_img.base_type*2+1,
				make_frame_name(frame_num),
				100,	# opacity
				NORMAL_MODE
			)
			pdb.gimp_image_insert_layer(new_img, new_layer, None, len(new_img.layers))
			pasted_layer = pdb.gimp_edit_paste(new_layer, 0) # 0 = clear selection in the new image
			pdb.gimp_floating_sel_anchor(pasted_layer)
			
			frame_col = frame_num % num_cols
			frame_row = int((frame_num - frame_col) / num_cols)
			pdb.gimp_layer_set_offsets(new_layer, frame_col*img.width, frame_row*img.height)

register(
	"python_fu_narly_sprite_export_sprite_sheet",	# unique name for plugin
	"Narly Sprite Export Sprite Sheet",		# short name
	"Narly Sprite Export Sprite Sheet",	# long name
	COPYRIGHT1,
	COPYRIGHT2,
	COPYRIGHT_YEAR,	# copyright year
	"<Image>/Sprite/Export/Sprite Sheet",	# what to call it in the menu
	"*",	# used when creating a new image (blank), else, use "*" for all existing image types
	[
		(PF_RADIO, "sheet_type", "Sprite Sheet Type", True,
			(
				("Horizontal", HORIZONTAL),
				("Grid", GRID),
			)
		),
	],	# input params,
	[],	# output params,
	narly_sprite_export_sprite_sheet	# actual function
)

# -----------------------------------------------
# -----------------------------------------------
# -----------------------------------------------

def narly_sprite_play_animation(img, layer):
	pdb.gimp_undo_push_group_start(img)
	pdb.gimp_undo_push_group_end(img)

register(
	"python_fu_narly_sprite_play_animation",	# unique name for plugin
	"Narly Sprite Play Animation",		# short name
	"Narly Sprite Play Animation",	# long name
	COPYRIGHT1,
	COPYRIGHT2,
	COPYRIGHT_YEAR,	# copyright year
	"<Image>/Sprite/Play Animation",	# what to call it in the menu
	"*",	# used when creating a new image (blank), else, use "*" for all existing image types
	[],	# input params,
	[],	# output params,
	narly_sprite_play_animation	# actual function
)


# -----------------------------------------------
# -----------------------------------------------
# -----------------------------------------------

def narly_sprite_delete_frame(img, layer):
	curr_frame_num = get_frame_num(layer)
	if curr_frame_num is None:
		return
	
	pdb.gimp_undo_push_group_start(img)

	frame_root = get_frame_root(layer)
	pdb.gimp_image_remove_layer(img, frame_root)
	shift_frames_up(img, curr_frame_num+1)
	if not goto_frame(img, curr_frame_num):
		goto_frame(img, curr_frame_num-1)

	pdb.gimp_undo_push_group_end(img)

register(
	"python_fu_narly_sprite_del_frame",	# unique name for plugin
	"Narly Sprite Delete Frame",		# short name
	"Narly Sprite Delete Frame",	# long name
	COPYRIGHT1,
	COPYRIGHT2,
	COPYRIGHT_YEAR,	# copyright year
	"<Image>/Sprite/Frames/Delete",	# what to call it in the menu
	"*",	# used when creating a new image (blank), else, use "*" for all existing image types
	[],	# input params,
	[],	# output params,
	narly_sprite_delete_frame	# actual function
)

# -----------------------------------------------
# -----------------------------------------------
# -----------------------------------------------

def narly_sprite_new_frame(img, layer):
	# means that we're currently in a valid frame, so
	# insert a new frame after this one, copying all the layers
	# and shifting all the subsequent frames down
	if layer is not None and get_frame_num(layer) is not None:
		pdb.gimp_undo_push_group_start(img)

		curr_frame_num = get_frame_num(layer)
		frame_root = get_frame_root(layer)
		curr_frame_position = pdb.gimp_image_get_layer_position(img, frame_root)

		# shift down any frames after the current one so we leave an
		# opening for the new frame
		shift_frames_down(img, curr_frame_num+1)

		# make the new frame's folder and add it to the image
		new_frame_root = pdb.gimp_layer_group_new(img)
		new_frame_root.name = make_frame_name(curr_frame_num+1)
		pdb.gimp_image_insert_layer(img, new_frame_root, None, curr_frame_position+1)

		# copy any layers in the current frame to the
		# new frame
		for frame_layer in frame_root.children:
			copied_layer = frame_layer.copy()
			copied_layer.name = frame_layer.name
			pdb.gimp_image_insert_layer(img, copied_layer, new_frame_root, len(new_frame_root.children))

		goto_frame(img, curr_frame_num+1)

		pdb.gimp_undo_push_group_end(img)

		return
	
	pdb.gimp_undo_push_group_start(img)

	# making it here means that we're not currently in a valid frame, so
	# just make the frame folder, add a frame layer, and be done with it
	# (it automatically adds the frame at the end)
	last_frame_num = get_last_frame_num(img)
	new_frame_root = pdb.gimp_layer_group_new(img)
	new_frame_root.name = make_frame_name(last_frame_num+1)
	pdb.gimp_image_insert_layer(img, new_frame_root, None, get_last_frame_position(img)+1)

	# add a blank new layer
	blank_layer = pdb.gimp_layer_new(
		img,
		img.width,
		img.height,
		img.base_type*2+1,	# RBGA_IMAGE,etc - always include the alpha TODO: change this?
		"Layer 1",	# layer name
		100,	# opacity
		NORMAL_MODE	# layer combination mode
	)
	pdb.gimp_image_insert_layer(img, blank_layer, new_frame_root, 0)

	goto_frame(img, last_frame_num+1)

	pdb.gimp_undo_push_group_end(img)

register(
	"python_fu_narly_sprite_new_frame",	# unique name for plugin
	"Narly Sprite New Frame",		# short name
	"Narly Sprite New Frame",	# long name
	COPYRIGHT1,
	COPYRIGHT2,
	COPYRIGHT_YEAR,	# copyright year
	"<Image>/Sprite/Frames/New",	# what to call it in the menu
	"*",	# used when creating a new image (blank), else, use "*" for all existing image types
	[],	# input params,
	[],	# output params,
	narly_sprite_new_frame	# actual function
	#menu="<Image>/Sprite/Frames"
)

# -----------------------------------------------
# -----------------------------------------------
# -----------------------------------------------

def narly_sprite_prev_frame(img, layer):
	curr_frame_num = get_frame_num(layer)
	if curr_frame_num is None:
		return
	
	if curr_frame_num <= 0:
		return
	
	goto_frame(img, curr_frame_num-1)

register(
	"python_fu_narly_sprite_prev_frame",	# unique name for plugin
	"Narly Sprite Prev Frame",		# short name
	"Narly Sprite Prev Frame",	# long name
	COPYRIGHT1,
	COPYRIGHT2,
	COPYRIGHT_YEAR,	# copyright year
	"<Image>/Sprite/Frames/Prev",	# what to call it in the menu
	"*",	# used when creating a new image (blank), else, use "*" for all existing image types
	[],	# input params,
	[],	# output params,
	narly_sprite_prev_frame	# actual function
)

# -----------------------------------------------
# -----------------------------------------------
# -----------------------------------------------

def narly_sprite_next_frame(img, layer):
	curr_frame_num = get_frame_num(layer)
	if curr_frame_num is None:
		return
	
	last_frame_num = get_last_frame_num(img)

	if curr_frame_num >= last_frame_num:
		return
	
	goto_frame(img, curr_frame_num+1)

register(
	"python_fu_narly_sprite_next_frame",	# unique name for plugin
	"Narly Sprite Next Frame",		# short name
	"Narly Sprite Next Frame",	# long name
	COPYRIGHT1,
	COPYRIGHT2,
	COPYRIGHT_YEAR,	# copyright year
	"<Image>/Sprite/Frames/Next",	# what to call it in the menu
	"*",	# used when creating a new image (blank), else, use "*" for all existing image types
	[],	# input params,
	[],	# output params,
	narly_sprite_next_frame	# actual function
)

# -----------------------------------------------
# -----------------------------------------------
# -----------------------------------------------

def narly_sprite_create(width, height, image_type):
	img = gimp.Image(width, height, image_type)

	narly_sprite_new_frame(img, None)

	gimp.Display(img)
	gimp.displays_flush()

register(
	"python_fu_narly_sprite_new",	# unique name for plugin
	"Narly Sprite",		# short name
	"Narly Sprite",	# long name
	COPYRIGHT1,
	COPYRIGHT2,
	COPYRIGHT_YEAR,	# copyright year
	"Sprite",	# what to call it in the menu
	"",	# used when creating a new image (blank), else, use "*"
	[
		(PF_INT16, "width", "Width for the sprite", 64),
		(PF_INT16, "height", "Height for the sprite", 64),
		(PF_RADIO, "image_type", "Image Type", True,
			(("RGB", RGB),
			("Grayscale", GRAY),
			("Indexed", INDEXED))
		),
	],	# input params,
	[],	# output params,
	narly_sprite_create,	# actual function
	menu="<Image>/File/Create"
)

if __name__ == "__main__":
	main()
