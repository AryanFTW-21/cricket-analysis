# Estimating Bat Speed from Broadcast Cricket Video
**Part 1 — System Design**

## 1. Problem
Estimate a cricket bat's speed across a swing from ordinary broadcast video, using a historical sensor library containing millions of unpaired shots. The sensor library includes overall metrics and approximately 100 samples per swing, including bat speed and impact speed.

Because the sensor shots are not paired with video, the library cannot directly supervise a video-to-speed model. It can provide realistic swing profiles and statistical priors, while video provides evidence about the particular shot.

## 2. Proposed pipeline

1. **Shot segmentation:** detect the delivery, swing, impact, and follow-through. Identify hard cuts, graphic wipes, and slow-motion replays. Preserve timestamps and playback-speed information.
2. **Batter tracking:** detect and consistently track the striker. Run a pose estimator on a cropped, upscaled batter region to estimate wrists, elbows, and shoulders. Store confidence and visibility for every frame.
3. **Bat tracking:** detect the handle and toe using a dedicated detector or segmentation followed by line fitting. Estimate bat angle and its uncertainty.
4. **Camera compensation:** track background features while masking the batter and static overlays. Estimate pan and zoom. Where pitch markings are visible, use cricket-ground geometry to estimate a pitch-plane homography.
5. **Metric scale and 3D reasoning:** use known pitch and stump dimensions where visible. A single broadcast view cannot fully recover motion toward or away from the camera, so quantify this ambiguity rather than hiding it.
6. **Hand-to-bat kinematics:** wrist velocity is not bat velocity. For a rigid bat, point velocity can be approximated by `v_point = v_grip + omega × r`, where `r` runs from the grip to the target point and `omega` is angular velocity. Confirm the exact bat reference point used by the sensor.
7. **Sensor prior:** align sensor curves to impact where possible and model typical curve shapes by shot type. Start with PCA or another interpretable low-dimensional model. Fit the prior to the observed video evidence, weighted by independent tracking quality.
8. **Synthetic pairs:** if sensor orientation or angular-rate channels exist, reconstruct plausible bat motion, infer hand trajectories using a documented kinematic model, project into randomized camera views, and simulate frame sampling, blur, occlusion, and tracking noise. Synthetic performance must not be presented as real-world accuracy.
9. **Output:** return a time-aligned speed curve, peak speed, impact speed, uncertainty intervals, and a quality flag. Abstain when the visual evidence is insufficient.

## 3. What the sensor library contributes
- Typical swing-curve shape and timing
- Relationships between peak speed and impact speed
- Variation by shot type and player
- Orientation or angular-rate channels, if available, to support the kinematic bridge

The prior must not simply force every video estimate toward an average swing.

## 4. Assumptions to confirm
- Whether speed is measured at the toe, sweet spot, or another point
- The definition and timestamp of impact speed
- Whether sensor orientation/angular-rate channels are available
- Whether footage is real-time or slow motion
- Whether pitch markings and stumps are sufficiently visible for calibration

## 5. Validation
The strongest test is a paired dataset of a few hundred sensor-equipped shots recorded with high-speed reference video. Split by player or session and report peak-speed MAE, impact-speed MAE, time-aligned curve RMSE, uncertainty coverage, and abstention rate.

Also evaluate on held-out synthetic data, but label this as simulation-only. Run ablations without the sensor prior, without camera compensation, and after downsampling high-speed footage to broadcast frame rate. Cross-view consistency and ball-motion checks can provide weaker sanity checks.

## 6. Main risks
- Motion blur and sparse frames near peak speed
- Camera pan, zoom, cuts, and graphics
- Wrist swaps and incorrect player identity
- Occlusion from gloves, bat, pads, or other players
- Depth ambiguity in a single view
- Domain shift between the sensor library and broadcast players
- Mismatch between the sensor's speed definition and the point inferred from video

## 7. Current prototype
The implemented baseline runs an off-the-shelf pose model on cricket clips and plots smoothed wrist image-plane velocity in pixels per second. It demonstrates a real-footage tracking workflow, but it does not yet provide calibrated bat speed, full camera compensation, bat orientation, or paired sensor validation. Those limitations are stated explicitly.
