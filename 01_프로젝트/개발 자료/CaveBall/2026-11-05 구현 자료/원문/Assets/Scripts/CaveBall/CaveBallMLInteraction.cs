using System.Collections;
using System.Collections.Generic;
using CellBig.Module.RTPoseSeg;
using HumanoidPoseControl;
using UnityEngine;

public sealed class CaveBallMLInteraction : MonoBehaviour
{
    private sealed class PoseFrameWithDimensions : PoseFrame
    {
        // The unmodified postprocessor discovers conventional dimension names
        // through reflection.
        public int width;
        public int height;
    }

    private const int LeftWristIndex = (int)KeypointOrder_YOLO.LeftWrist;
    private const int RightWristIndex = (int)KeypointOrder_YOLO.RightWrist;
    private static int FrontEffectsLayer
    {
        get
        {
            int layer = LayerMask.NameToLayer("UIEffect");
            return layer >= 0 ? layer : 9;
        }
    }

    private readonly List<GameObject> _leftEffects = new();
    private readonly List<GameObject> _rightEffects = new();

    private CaveBall _ball;
    private CaveBallSetting _settings;
    private Camera _frontCamera;
    private HumanPosePostprocessor _postprocessor;
    private CaveBallSilhouetteView _silhouetteView;
    private Coroutine _startCoroutine;
    private bool _listening;
    private bool _moduleStarted;
    private float _lastPoseTime = float.NegativeInfinity;

    public void Initialize(CaveBall ball, CaveBallSetting settings, Camera frontCamera)
    {
        _ball = ball;
        _settings = settings;
        _frontCamera = frontCamera;
        _postprocessor = GetComponent<HumanPosePostprocessor>();
        if (_postprocessor == null)
        {
            _postprocessor = gameObject.AddComponent<HumanPosePostprocessor>();
        }

        _silhouetteView = gameObject.AddComponent<CaveBallSilhouetteView>();
        _silhouetteView.Initialize(frontCamera, settings);
        GameObject leftTemplate = FindHandEffect("RedEffect");
        GameObject rightTemplate = FindHandEffect("BlueEffect");
        CreateEffectSlots(leftTemplate, _leftEffects, settings.MaxTrackedPeople);
        CreateEffectSlots(rightTemplate, _rightEffects, settings.MaxTrackedPeople);
        SetEffectsVisible(false);
    }

    public void StartSession()
    {
        if (_listening)
        {
            return;
        }

        Message.AddListener<RTPoseOutputMsg>(OnPoseOutput);
        Message.AddListener<RTSegOutputMsg>(OnSegOutput);
        _listening = true;
        _startCoroutine = StartCoroutine(StartWhenModuleReady());
    }

    public void StopSession()
    {
        if (_startCoroutine != null)
        {
            StopCoroutine(_startCoroutine);
            _startCoroutine = null;
        }

        if (_listening)
        {
            Message.RemoveListener<RTPoseOutputMsg>(OnPoseOutput);
            Message.RemoveListener<RTSegOutputMsg>(OnSegOutput);
            _listening = false;
        }

        if (_moduleStarted)
        {
            RTPoseSegLease.Release(
                GetInstanceID(),
                pose: true,
                segmentation: true);
            _moduleStarted = false;
        }

        SetEffectsVisible(false);
    }

    private IEnumerator StartWhenModuleReady()
    {
        while (_listening)
        {
            RTPoseSegDataModel model = Model.First<RTPoseSegDataModel>();
            if (model != null && model._isInitialized)
            {
                RTPoseSegLease.Acquire(
                    GetInstanceID(),
                    pose: true,
                    segmentation: true);
                _moduleStarted = true;

                if (model._liveMaskTexture != null)
                {
                    _silhouetteView.SetMask(model._liveMaskTexture);
                }

                _startCoroutine = null;
                yield break;
            }

            yield return null;
        }
    }

    private void Update()
    {
        if (_listening && Time.unscaledTime - _lastPoseTime > _settings.PoseTimeout)
        {
            SetEffectsVisible(false);
        }

#if UNITY_EDITOR
        if (_listening && Input.GetKeyDown(KeyCode.R))
        {
            _ball.TryApplyHandColor(CaveBallState.Red);
        }
        if (_listening && Input.GetKeyDown(KeyCode.B))
        {
            _ball.TryApplyHandColor(CaveBallState.Blue);
        }
#endif
    }

    private void OnDestroy()
    {
        StopSession();
    }

    private void OnPoseOutput(RTPoseOutputMsg message)
    {
        PoseFrame frame = message.poseFrame;
        if (frame?.people == null)
        {
            return;
        }

        PoseFrame processed = frame;
        if (_postprocessor != null)
        {
            PoseFrameWithDimensions processFrame = new PoseFrameWithDimensions
            {
                timestampMs = frame.timestampMs,
                resolution = frame.resolution,
                people = frame.people,
                width = frame.resolution.x,
                height = frame.resolution.y
            };
            processed = _postprocessor.Process(processFrame);
        }
        if (processed?.people == null || processed.people.Count == 0)
        {
            SetEffectsVisible(false);
            return;
        }

        int trackedCount = Mathf.Min(
            processed.people.Count,
            Mathf.Min(_leftEffects.Count, _rightEffects.Count));
        for (int i = 0; i < trackedCount; i++)
        {
            TrackedPersonPose person = processed.people[i];
            bool validPose = person?.keypoints != null &&
                             person.keypoints.Length > RightWristIndex;
            bool hasLeft = validPose && UpdateHand(
                person.keypoints[LeftWristIndex],
                _leftEffects[i],
                CaveBallState.Red);
            bool hasRight = validPose && UpdateHand(
                person.keypoints[RightWristIndex],
                _rightEffects[i],
                CaveBallState.Blue);

            SetEffectVisible(_leftEffects[i], hasLeft);
            SetEffectVisible(_rightEffects[i], hasRight);
        }

        _lastPoseTime = Time.unscaledTime;
        HideUnusedEffectSlots(trackedCount);
    }

    private void OnSegOutput(RTSegOutputMsg message)
    {
        _silhouetteView.SetMask(message.mask);
    }

    private bool UpdateHand(Keypoint wrist, GameObject effect, CaveBallState handColor)
    {
        if (wrist.score < _settings.MinimumWristConfidence || _frontCamera == null)
        {
            return false;
        }

        Vector2 viewport = wrist.pos;
        if (_settings.MirrorPoseX) viewport.x = 1f - viewport.x;
        if (_settings.InvertPoseY) viewport.y = 1f - viewport.y;

        Vector3 handWorld = _frontCamera.ViewportToWorldPoint(
            new Vector3(viewport.x, viewport.y, _settings.FrontInteractionDepth));
        if (effect != null)
        {
            effect.transform.position = handWorld;
        }

        Vector3 ballViewport = _frontCamera.WorldToViewportPoint(_ball.transform.position);
        if (ballViewport.z <= 0f)
        {
            return true;
        }

        float handRadius = _settings.HandContactViewportRadius;
        Rect handRect = Rect.MinMaxRect(
            viewport.x - handRadius,
            viewport.y - handRadius,
            viewport.x + handRadius,
            viewport.y + handRadius);
        Rect ballRect = GetBallViewportRect(ballViewport);
        if (handRect.Overlaps(ballRect))
        {
            _ball.TryApplyHandColor(handColor);
        }

        return true;
    }

    private GameObject FindHandEffect(string objectName)
    {
        foreach (Transform child in transform.GetComponentsInChildren<Transform>(true))
        {
            if (child.name != objectName)
            {
                continue;
            }

            SetLayerRecursively(child, FrontEffectsLayer);

            if (_frontCamera != null)
            {
                _frontCamera.cullingMask |= 1 << FrontEffectsLayer;
            }

            return child.gameObject;
        }

        Debug.LogError($"[CaveBallMLInteraction] CaveballBG에서 '{objectName}'을 찾지 못했습니다.");
        return null;
    }

    private Rect GetBallViewportRect(Vector3 ballViewport)
    {
        SphereCollider ballCollider = _ball.GetComponent<SphereCollider>();
        if (ballCollider == null)
        {
            return new Rect(ballViewport.x, ballViewport.y, 0f, 0f);
        }

        Bounds bounds = ballCollider.bounds;
        Vector3 min = bounds.min;
        Vector3 max = bounds.max;
        float minX = float.PositiveInfinity;
        float minY = float.PositiveInfinity;
        float maxX = float.NegativeInfinity;
        float maxY = float.NegativeInfinity;

        for (int x = 0; x <= 1; x++)
        {
            for (int y = 0; y <= 1; y++)
            {
                for (int z = 0; z <= 1; z++)
                {
                    Vector3 corner = new Vector3(
                        x == 0 ? min.x : max.x,
                        y == 0 ? min.y : max.y,
                        z == 0 ? min.z : max.z);
                    Vector3 projected = _frontCamera.WorldToViewportPoint(corner);
                    if (projected.z <= 0f)
                    {
                        continue;
                    }

                    minX = Mathf.Min(minX, projected.x);
                    minY = Mathf.Min(minY, projected.y);
                    maxX = Mathf.Max(maxX, projected.x);
                    maxY = Mathf.Max(maxY, projected.y);
                }
            }
        }

        if (float.IsInfinity(minX))
        {
            return new Rect(ballViewport.x, ballViewport.y, 0f, 0f);
        }

        return Rect.MinMaxRect(minX, minY, maxX, maxY);
    }

    private void SetEffectsVisible(bool visible)
    {
        foreach (GameObject effect in _leftEffects)
        {
            SetEffectVisible(effect, visible);
        }
        foreach (GameObject effect in _rightEffects)
        {
            SetEffectVisible(effect, visible);
        }
    }

    private void CreateEffectSlots(
        GameObject template,
        List<GameObject> slots,
        int requestedCount)
    {
        slots.Clear();
        if (template == null)
        {
            return;
        }

        slots.Add(template);
        int count = Mathf.Max(1, requestedCount);
        for (int i = 1; i < count; i++)
        {
            GameObject clone = Instantiate(template, transform);
            clone.name = $"{template.name} Player {i + 1}";
            SetLayerRecursively(clone.transform, FrontEffectsLayer);
            clone.SetActive(false);
            slots.Add(clone);
        }
    }

    private void HideUnusedEffectSlots(int usedCount)
    {
        for (int i = usedCount; i < _leftEffects.Count; i++)
        {
            SetEffectVisible(_leftEffects[i], false);
        }
        for (int i = usedCount; i < _rightEffects.Count; i++)
        {
            SetEffectVisible(_rightEffects[i], false);
        }
    }

    private static void SetEffectVisible(GameObject effect, bool visible)
    {
        if (effect == null || effect.activeSelf == visible)
        {
            return;
        }

        effect.SetActive(visible);
        foreach (ParticleSystem particles in effect.GetComponentsInChildren<ParticleSystem>(true))
        {
            if (visible)
            {
                particles.Play(true);
            }
            else
            {
                particles.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            }
        }
    }

    private static void SetLayerRecursively(Transform root, int layer)
    {
        foreach (Transform child in root.GetComponentsInChildren<Transform>(true))
        {
            child.gameObject.layer = layer;
        }
    }

    private void OnDisable()
    {
        SetEffectsVisible(false);
    }
}
