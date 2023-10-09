import bpy
import os
import random
import math

"""
Creates VSE clips and mouth shape-key keyframes to approximate a given
dialogue. Simmilar to Animal Crossing's "animalese"
"""

def load_letter_audio(directory, letter, start_frame, duration):
    """
    Given a directory of WAV files, select the correct clip for the desired letter,
    then grab a random segment form the middle of the wav, and add it to the VSE
    """
    # Get all files in the directory
    files = [f for f in os.listdir(directory) if f.endswith('.wav')]
    
    # Switch to Video Editing workspace to ensure the right context
    prev_area_type = bpy.context.area.type
    bpy.context.area.type = 'SEQUENCE_EDITOR'
    
    # Check if a desired wav exists containing the letter
    matches = [f for f in files if letter in f]
    # If we can't find it, choose randomly from all
    if not matches:
        matches = files
    
    strip = bpy.ops.sequencer.sound_strip_add(
        filepath=os.path.join(directory, random.choice(matches)),
        channel=1
    )
        
    # Modify the duration to match the letter_duration
    active_strip = bpy.context.scene.sequence_editor.active_strip
    total_frames = active_strip.frame_final_end - active_strip.frame_final_start

    clip_start = random.randint(active_strip.frame_final_start, total_frames)
    active_strip.frame_final_start = clip_start
    active_strip.frame_final_end = clip_start + duration
    active_strip.frame_start = start_frame - clip_start

    # Switch back to previous workspace after adding the sound strip
    bpy.context.area.type = prev_area_type
    
def get_mouth_shape_keys(mouth_obj):
    """
    Return the only shape keys we care about, the ones prefixed with:
    '#'
    """
    return [
        key for key in mouth_obj.data.shape_keys.key_blocks
        if key.name.startswith("#")
    ]

def set_rest_mouth(mouth, current_frame, duration_frames):
    """
    Set all mouth shapes to '0', placing the mouth 'at rest'
    """
    for shape_key in get_mouth_shape_keys(mouth):
        shape_key.value = 0
        shape_key.keyframe_insert(data_path='value', frame=current_frame)
        shape_key.keyframe_insert(data_path='value', frame=current_frame + duration_frames)

def select_shape_key(mouth, letter):
    """
    For the given char letter, return the mouth's shape key that matches
    (or a random one, if the desired letter is missing)
    """
    matches = [
        shape_key for shape_key
        in get_mouth_shape_keys(mouth)
        if letter in shape_key.name
    ]
    
    if matches:
        shape = random.choice(matches)
        shape.value = 1
        return shape
    else:
        # Random shape key activation if the desired one doesn't exist
        random_shape = random.choice(mouth.data.shape_keys.key_blocks)
        random_shape.value = 1
        return random_shape

def set_mouth(mouth, char, current_frame, duration_frames):
    """
    Set the mouth shape to fit the desired char
    """
    active_key = select_shape_key(mouth, char)
    active_key.keyframe_insert(data_path='value', frame=current_frame)
    active_key.keyframe_insert(data_path='value', frame=current_frame + duration_frames)

def split_dialogue_to_segments(dialogue, max_letters=20):
    """
    Given the string of dialogue, split it to small segments that
    can fit on screen
    """
    segments = []
    segment = ''
    for char in dialogue:
        segment += char
        line_ended = char in ".,!?\n" and len(segment) > (max_letters/4)
        word_ended = char in " " and len(segment) > max_letters

        if line_ended or word_ended:
            segments.append(segment.strip())
            segment = ''

    if segment:  # For the final segment
        segments.append(segment)
    return segments

def create_text(segment):
    # Create the text object
    bpy.ops.object.text_add()
    text_obj = bpy.context.object
    text_obj.data.body = segment.replace("\n", "")

    # Force an update of the scene
    # (without this, the obj will read the default 'text'
    # when viewed in the blender viewport)
    bpy.context.view_layer.update()

    # Set horizontal alignment to center
    text_obj.data.align_x = 'CENTER'
    # Set a good transform
    text_obj.scale = (0.1, 0.1, 0.1)
    text_obj.rotation_euler[0] = math.radians(90)
    text_obj.location = (0, -1, 1)

    # Check if a material named 'Subtitle' exists; if not, create it
    material = bpy.data.materials.get("Subtitle")
    if not material:
        material = bpy.data.materials.new(name="Subtitle")
    
    # Assign the material to the text object
    if text_obj.data.materials:
        text_obj.data.materials[0] = material
    else:
        text_obj.data.materials.append(material)

    # Add to subtitles collection
    bpy.context.collection.objects.unlink(text_obj)
    bpy.data.collections['subtitles'].objects.link(text_obj)
    return text_obj

def keyframe_subtitle_visibility(text_obj, frame, visible: bool, scale_value=(0.1, 0.1, 0.1)):
    """
    Keyframe the visiblity at 'frame' to true/false
    """
    text_obj.scale = scale_value if visible else (0, 0, 0)
    text_obj.keyframe_insert(data_path="scale", frame=frame)

def set_marker(name, frame):
    marker = bpy.context.scene.timeline_markers.new("#"+name, frame=int(frame))

def get_segment_markers(prefix="#"):
    """
    Return only the markers that are used for speech
    e.g., those prefixed with '#'
    """
    return [
        m for m in bpy.context.scene.timeline_markers
        if m.name.startswith(prefix)
    ]

def clear_markers():
    scene = bpy.context.scene
    for m in get_segment_markers():
        scene.timeline_markers.remove(m)

def clear_collection(collection_name):
    """
    Clear all objects from the specified collection.
    """
    if collection_name in bpy.data.collections:
        collection = bpy.data.collections[collection_name]
        for obj in collection.objects:
            bpy.data.objects.remove(obj, do_unlink=True)

def clear_mouth_keyframes(mouth):
    """
    All the 'mouth' keyframes start with #
    - clear them before continuing
    """
    if not mouth.data.shape_keys or not mouth.data.shape_keys.animation_data:
        return
    action = mouth.data.shape_keys.animation_data.action
    if not action:
        return
    # Fetch only the relevant shape keys
    relevant_shape_key_names = [key.name for key in get_mouth_shape_keys(mouth)]
    for fcurve in action.fcurves:
        # Only remove keyframes for the shape keys we care about
        if any(name in fcurve.data_path for name in relevant_shape_key_names):
            fcurve.keyframe_points.clear()

def clear_vse():
    bpy.context.window.workspace = bpy.data.workspaces["Video Editing"]
    bpy.context.scene.sequence_editor_clear()
    
def get_duration_frames(letter_duration):
    """
    Given a time (in seconds) we want each letter to roughtly last,
    return the # of frames, at the current framerate, each letter would last
    """
    # TODO could switch to a system where it is based on dialoge length and project length?
    framerate = bpy.context.scene.render.fps
    duration_frames = int(letter_duration * framerate)
    if duration_frames < 1:
        raise ValueError(f"{letter_duration} duration and {framerate} framerate caused {duration_frames} duration_frames")
    return duration_frames

def get_segment_length(segment, duration_frames=1):
    """
    Given a segment string, and how many frames we want each
    'letter' to take to say, return the total number of frames
    this segment will last
    - given that we pause longer on punctuation
    """
    frames = 0
    for char in segment:
        char = char.lower()
        frames += duration_frames
        if char in '.,!?':
            frames += 5 * duration_frames
    return frames

def add_markers(dialogue, frame_margins=20):
    """Split the dialogue into segments and place markers for each segment."""
    start_frame = frame_margins
    last_frame = bpy.context.scene.frame_end - frame_margins
    talking_frames = last_frame - start_frame

    # Clear any previous markers
    clear_markers()

    current_frame = start_frame
    segments = split_dialogue_to_segments(dialogue)
    frames_per_marker = talking_frames / len(segments)

    for segment in segments:
        # Marker the start of a segment
        set_marker(segment, current_frame)
        current_frame += frames_per_marker
        
def add_speech_to_markers(dialogue, directory, audio=False):
    """
    Create subtitles, animate mouth shapes, and add audio,
    based on the markers present from
    """
    markers = get_segment_markers()
    segments = split_dialogue_to_segments(dialogue)

    # Get the 'mouth' object
    mouth = bpy.data.objects.get('mouth')
    if not mouth:
        raise ValueError("No 'mouth' object found.")

    # Clear any data from a previous run
    clear_collection('subtitles')
    clear_mouth_keyframes(mouth)
    # Remove previous strips from VSE
    if (audio):
        clear_vse()

    # Check if the 'subtitles' collection exists, if not create it
    if 'subtitles' not in bpy.data.collections:
        subtitles_collection = bpy.data.collections.new('subtitles')
        bpy.context.scene.collection.children.link(subtitles_collection)
    else:
        subtitles_collection = bpy.data.collections['subtitles']

    # Start the mouth as 'at rest'
    start_frame = markers[0].frame
    set_rest_mouth(mouth, start_frame-1, 1)

    # Iterate through each segment/marker, making 
    assert len(markers) == len(segments)
    for i in range(len(segments)):
        # Use marker's frame as starting point
        segment = segments[i]
        marker = markers[i]
        next_marker = markers[i+1] if i+1 < len(markers) else None

        segment_start = marker.frame
        segment_end = next_marker.frame if next_marker else bpy.context.scene.frame_end

        # How many frames we get to spend on each letter
        duration_frames = (segment_end - segment_start) // get_segment_length(segment)
        print(f"Starting: {segment_start}-{segment_end} ({duration_frames}) {segment}")
        # TODO for now, just make sure it can't be 0 - we will cut it off
        # if needed
        duration_frames = max(1, duration_frames)

        # Create and set up text object for this segment
        text_obj = create_text(segment)
        # All subtitles can be 'visible' on frame 0
        # (to ease editing in viewport)
        keyframe_subtitle_visibility(text_obj, 0, True)
        # But they are invisible from 1 to just before they are needed
        keyframe_subtitle_visibility(text_obj, 1, False)
        keyframe_subtitle_visibility(text_obj, segment_start-1, False)
        # And becomes visible at the start of this segment
        keyframe_subtitle_visibility(text_obj, segment_start, True)
        # And becomes invisible again after end of segment
        keyframe_subtitle_visibility(text_obj, segment_end-1, True)
        keyframe_subtitle_visibility(text_obj, segment_end, False)

        # Animate mouth and optionally load audio for each character
        current_frame = segment_start
        for char in segment:
            char = char.lower()
            set_rest_mouth(mouth, current_frame, duration_frames)

            if char in 'abcdefghijklmnopqrstuvwxyz':
                if audio:
                    load_letter_audio(directory, char, current_frame, duration_frames)
                set_mouth(mouth, char, current_frame, duration_frames)
            
            current_frame += duration_frames
            if char in '.,!?':
                current_frame += 5 * duration_frames
            # TODO for now, if we go over, just go to next
            if current_frame >= segment_end:
                break

    # Finish up
    bpy.context.window.workspace = bpy.data.workspaces["Layout"]
    # For now, let's select these new objects
    bpy.ops.object.select_all(action='DESELECT')
    mouth.select_set(True)
    for text_obj in subtitles_collection.objects:
        text_obj.select_set(True)

def main(redo_markers=False):
    # Update with your desired dialogue, directory path, letter_duration:
    dialogue = """
    Is this running? Yes.
    Listen close - I'll speak quickly because I don't have much tape.

    And I don't know how many of these I can safely.. Distribute.

    Okay. You asked:
    "In communism, is there a currency? How is it managed?"

    Historically, the Soviet Union, China, and Cuba all danced with currencies, every twist orchestrated by the authoritarian state.

    But ah, mon ami, let us indulge in a little fantasy, shall we? Imagine, if you will, an ideal communist society – 
    "ideal", but let's keep one foot in reality. 

    "From each according to his ability, to each according to his needs"
    - a beautiful mantra, non?
    A library economy - use what you need, borrow what you want, return when you are done.
    No money needed. But how do we get there?

    Marx whispered about 'Labour Vouchers'. Given for your hours of toil, they are spent once and then... poof, vanished, no chance for hoarding. Today, these would be digital, decentralized, perhaps blockchain. But it has much the same stench as cash.

    And trading with the outside world? Ah, it gets murky. Fixed rate agreements, or anchored to commodities, diversified reserves - perhaps I will save it for another day.

    "Participatory Economics" touts the strength of decentralized planning - letting the communities vote on how their stockpiles are filled, trying to sidestep the bureaucratic failures of the past.

    And economies should not be written in stone, by men in gray suits. The feedback systems need to be in a constant dance. If vouchers are in play, then whenever shortage is reported, the value grows in real time. No rigid central planning, no hoarding, no monopoly.

    But ah, the challenges. Even transitory vouchers risk inflation - and black-markets - but I will save that for another time.

    Remember, my friend, even in this imagined paradise, currency's dance has many steps. Eh, voilà!

    Eh. We didn't answer anything yet, but my tape is running out. Please, submit your follow up questions, I will do my best to answer what I can.

    For now, au revoir.
    """
    directory = "F:\\My-Blender\\blender-other\\Strings Attached - Puppet Code\\squeaks\\"

    # If we don't have markers, just add those, and let the user move them depending on
    # how they want the pacing.
    if (get_segment_markers() == [] or redo_markers == True):
        add_markers(dialogue)
    else:
        add_speech_to_markers(dialogue, directory)

# TODO WATCH REDO MARKERS
main()
