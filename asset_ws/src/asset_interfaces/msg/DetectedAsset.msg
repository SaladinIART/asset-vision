# One detected object in a frame.
# If asset_id is non-empty, the object was matched to a registered asset via QR.

std_msgs/Header header

string label          # YOLO class label (e.g. "laptop")
float32 confidence    # detection confidence 0.0-1.0
int32 x1              # bounding box top-left x
int32 y1              # bounding box top-left y
int32 x2              # bounding box bottom-right x
int32 y2              # bounding box bottom-right y
string asset_id       # e.g. "AV-0001" — empty if not linked to an asset
string qr_payload     # raw QR string decoded in this frame (empty if none)
