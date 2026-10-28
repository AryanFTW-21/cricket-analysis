# Prototype Results and Failure Analysis

## 1. Objective

The prototype evaluates whether an off-the-shelf pose estimator can track a batter's wrist in cricket footage and produce a motion profile over time. It is an initial component of a bat-speed estimation system, not a validated physical bat-speed estimator.

## 2. Method

The script processes each video, estimates wrist keypoints, smooths image coordinates, and differentiates the resulting trajectories to estimate wrist image-plane speed in pixels per second (px/s).

The outputs include tracking CSVs, velocity plots, annotated videos, and summary JSON files.

## 3. Experimental results

| Video | Resolution | FPS | Frames | Valid frames | Coverage | Suspected cuts | Peak wrist speed (px/s) |
|---|---|---:|---:|---:|---:|---:|---:|
| clip1.webm | 1280x720 | 25 | 125 | 87 | 69.6% | 1 | 3770.6 |
| clip2.mp4 | 608x1080 | 30 | 331 | 309 | 93.4% | 1 | 2138.3 |
| clip2.webm | 608x1080 | 30 | 331 | 320 | 96.7% | 1 | 2288.1 |
| clip3.mp4 | 1920x1080 | 25 | 350 | 195 | 55.7% | 2 | 5344.8 |
| clip3.webm | 1920x1080 | 25 | 350 | 194 | 55.4% | 2 | 5863.6 |

Coverage is the fraction of processed frames with a valid wrist observation according to the script. It is not a measurement of keypoint accuracy.

The clip2 variants have the highest tracking coverage, at 93.4% and 96.7%. The clip3 variants have the lowest, at 55.7% and 55.4%.

Peak pixel velocities should not be compared as physical speeds across clips. Resolution, camera distance, zoom, camera motion, and tracking errors affect image-plane motion. A larger value does not establish that a bat or player is moving faster.

## 4. Failure analysis

1. **Camera motion:** panning and zooming can contribute to apparent wrist movement. The current baseline does not fully compensate for camera motion.
2. **Motion blur:** fast swings can obscure wrist keypoints or cause unstable detections.
3. **Cuts and transitions:** the script flags suspected scene cuts, but simple cut detection can miss wipes or misclassify rapid motion.
4. **Identity and wrist selection:** selecting the largest person and highest-confidence wrist can result in identity changes or switching between wrists.
5. **Occlusion:** gloves, the bat, pads, and the torso can hide the wrist.
6. **Pixel scale:** px/s depends on the camera view and cannot be converted to m/s without suitable geometric calibration.
7. **Wrist-to-bat mismatch:** bat rotation can make the sweet spot move substantially faster or in a different direction than the wrist.

Tracking coverage alone cannot establish which failure caused each invalid observation. Specific frame-level failure claims should be made only after reviewing the corresponding annotated video and plot.

## 5. What is required for physical bat-speed estimation?

A defensible implementation needs consistent batter tracking, bat handle and toe or bat-axis tracking, camera-motion compensation, metric calibration, and a defined target point on the bat.

For a rigid bat, point velocity can be approximated by:

v_point = v_grip + omega x r

where v_grip is grip translation velocity, omega is bat angular velocity, and r is the vector from the grip to the target point.

A single broadcast view has depth ambiguity. Historical sensor curves can provide statistical priors, but unpaired sensor records are not direct ground-truth labels for individual video frames.

The completed system should be validated on paired video and sensor recordings. Suggested metrics include peak-speed MAE, impact-speed MAE, time-aligned curve RMSE, uncertainty coverage, and abstention rate.

## 6. Conclusion

The prototype demonstrates wrist tracking and pixel-velocity profiling on five video files. Tracking coverage varies from 55.4% to 96.7%, showing that usable observations depend on the footage.

These results are diagnostic evidence of a working baseline. They do not demonstrate calibrated bat speed or physical-speed accuracy. Camera compensation, bat tracking, metric calibration, uncertainty estimation, and paired validation remain necessary.
