# All detections from one frame, published by perception_node.

std_msgs/Header header    # stamp = frame capture time, frame_id = "camera"
DetectedAsset[] detections
int32 frame_width
int32 frame_height
float32 inference_ms      # YOLO inference time in milliseconds
