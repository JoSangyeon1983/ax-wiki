using System.Collections.Generic;
using CellBig.EdgeBlending;
using CellBig.Module;
using UnityEngine;

public sealed class CaveBallDisplayRig : MonoBehaviour
{
    private readonly Dictionary<string, Camera> _gameCameras = new();
    private readonly Dictionary<Camera, int> _originalUICameraDisplays = new();
    private readonly Dictionary<Canvas, int> _originalCanvasDisplays = new();
    private int _frontDisplay;
    private bool _frameworkUIApplied;
    private CaveBallSetting _settings;
    private EdgeBlendingManager _edgeBlendingManager;

    public Camera FrontCamera { get; private set; }
    public Camera FloorCamera { get; private set; }
    public Camera LeftCamera { get; private set; }
    public Camera RightCamera { get; private set; }

    public void Configure(CaveBallSetting settings)
    {
        _settings = settings;
        CacheGameCameras();
        ActivateDisplays(settings);

        SetTarget("LeftWallCamera", settings.LeftDisplay);
        SetTarget("FrontCamera", settings.FrontDisplay);
        SetTarget("RightWallCamera", settings.RightDisplay);
        SetTarget("FloorCamera", settings.FloorDisplay);

        FrontCamera = GetCamera("FrontCamera");
        FloorCamera = GetCamera("FloorCamera");
        LeftCamera = GetCamera("LeftWallCamera");
        RightCamera = GetCamera("RightWallCamera");

        _frontDisplay = settings.FrontDisplay;
        //if (FrontCamera != null)
        //{
        //    FrontCamera.clearFlags = CameraClearFlags.SolidColor;
        //    FrontCamera.backgroundColor = Color.black;
        //}

        ConfigureEdgeBlending();
        KeepSingleAudioListener();
    }

    public void ActivateSession()
    {
        if (_edgeBlendingManager == null)
        {
            ConfigureEdgeBlending();
        }

        if (_frameworkUIApplied)
        {
            return;
        }

        foreach (UICamera uiCamera in FindObjectsOfType<UICamera>(true))
        {
            ApplyCameraDisplay(uiCamera._Camera);
            ApplyCameraDisplay(uiCamera._KioskCamera);
            ApplyCanvasDisplay(uiCamera._Canvas);
            ApplyCanvasDisplay(uiCamera._KioskCanvas);
        }

        _frameworkUIApplied = true;
    }

    public void DeactivateSession()
    {
        if (!_frameworkUIApplied)
        {
            return;
        }

        foreach (KeyValuePair<Camera, int> entry in _originalUICameraDisplays)
        {
            if (entry.Key != null)
            {
                entry.Key.targetDisplay = entry.Value;
            }
        }

        foreach (KeyValuePair<Canvas, int> entry in _originalCanvasDisplays)
        {
            if (entry.Key != null)
            {
                entry.Key.targetDisplay = entry.Value;
            }
        }

        _frameworkUIApplied = false;
    }

    private void CacheGameCameras()
    {
        _gameCameras.Clear();
        foreach (Camera cameraComponent in GetComponentsInChildren<Camera>(true))
        {
            _gameCameras[cameraComponent.name] = cameraComponent;
        }
    }

    private static void ActivateDisplays(CaveBallSetting settings)
    {
        if (Application.isEditor)
        {
            return;
        }

        int[] requested =
        {
            settings.LeftDisplay,
            settings.FrontDisplay,
            settings.RightDisplay,
            settings.FloorDisplay
        };

        foreach (int displayIndex in requested)
        {
            if (displayIndex > 0 && displayIndex < Display.displays.Length)
            {
                Display.displays[displayIndex].Activate();
            }
        }
    }

    private void SetTarget(string cameraName, int displayIndex)
    {
        Camera cameraComponent = GetCamera(cameraName);
        if (cameraComponent != null)
        {
            cameraComponent.targetDisplay = Mathf.Max(0, displayIndex);
        }
        else
        {
            Debug.LogWarning($"[CaveBallDisplayRig] '{cameraName}' 카메라를 찾지 못했습니다.");
        }
    }

    private Camera GetCamera(string cameraName)
    {
        _gameCameras.TryGetValue(cameraName, out Camera cameraComponent);
        return cameraComponent;
    }

    private void ApplyCameraDisplay(Camera[] cameras)
    {
        if (cameras == null)
        {
            return;
        }

        foreach (Camera cameraComponent in cameras)
        {
            ApplyCameraDisplay(cameraComponent);
        }
    }

    private void ApplyCameraDisplay(Camera cameraComponent)
    {
        if (cameraComponent == null)
        {
            return;
        }

        if (!_originalUICameraDisplays.ContainsKey(cameraComponent))
        {
            _originalUICameraDisplays.Add(cameraComponent, cameraComponent.targetDisplay);
        }
        cameraComponent.targetDisplay = _frontDisplay;
    }

    private void ApplyCanvasDisplay(Canvas[] canvases)
    {
        if (canvases == null)
        {
            return;
        }

        foreach (Canvas canvas in canvases)
        {
            ApplyCanvasDisplay(canvas);
        }
    }

    private void ApplyCanvasDisplay(Canvas canvas)
    {
        if (canvas == null)
        {
            return;
        }

        if (!_originalCanvasDisplays.ContainsKey(canvas))
        {
            _originalCanvasDisplays.Add(canvas, canvas.targetDisplay);
        }
        canvas.targetDisplay = _frontDisplay;
    }

    private void OnDestroy()
    {
        if (_edgeBlendingManager != null)
        {
            _edgeBlendingManager.SystemStarted -= OnEdgeBlendingStarted;
        }
        DeactivateSession();
    }

    private void ConfigureEdgeBlending()
    {
        _edgeBlendingManager = FindObjectOfType<EdgeBlendingManager>();
        if (_edgeBlendingManager == null)
        {
            return;
        }

        _edgeBlendingManager.SystemStarted -= OnEdgeBlendingStarted;
        _edgeBlendingManager.SystemStarted += OnEdgeBlendingStarted;
        if (_edgeBlendingManager.IsStarted)
        {
            ApplyFloorBlendDisplays();
        }
    }

    private void OnEdgeBlendingStarted(EdgeBlendingSystemData systemData)
    {
        ApplyFloorBlendDisplays();
    }

    private void ApplyFloorBlendDisplays()
    {
        if (_settings?.FloorBlendDisplays == null ||
            _settings.FloorBlendDisplays.Length == 0 ||
            _edgeBlendingManager?.EdgeBlenders == null)
        {
            return;
        }

        int count = Mathf.Min(
            _settings.FloorBlendDisplays.Length,
            _edgeBlendingManager.EdgeBlenders.Count);
        for (int i = 0; i < count; i++)
        {
            EdgeBlender blender = _edgeBlendingManager.EdgeBlenders[i];
            if (blender?.Camera == null)
            {
                continue;
            }

            int targetDisplay = _settings.FloorBlendDisplays[i];
            if (targetDisplay == _frontDisplay)
            {
                blender.Camera.enabled = false;
                Debug.LogError(
                    $"[CaveBallDisplayRig] Floor EdgeBlender {i}가 FrontDisplay " +
                    $"{_frontDisplay}와 충돌하여 비활성화했습니다.");
                continue;
            }

            blender.Camera.targetDisplay = Mathf.Max(0, targetDisplay);
            blender.Camera.enabled = true;
            if (!Application.isEditor &&
                targetDisplay > 0 &&
                targetDisplay < Display.displays.Length)
            {
                Display.displays[targetDisplay].Activate();
            }
        }

        if (_settings.FloorBlendDisplays.Length != _edgeBlendingManager.EdgeBlenders.Count)
        {
            Debug.LogWarning(
                "[CaveBallDisplayRig] FloorBlendDisplays 수와 EdgeBlender 수가 다릅니다.");
        }
    }

    private void KeepSingleAudioListener()
    {
        AudioListener keeper = FrontCamera != null ? FrontCamera.GetComponent<AudioListener>() : null;
        foreach (AudioListener listener in GetComponentsInChildren<AudioListener>(true))
        {
            listener.enabled = listener == keeper;
        }
    }
}
