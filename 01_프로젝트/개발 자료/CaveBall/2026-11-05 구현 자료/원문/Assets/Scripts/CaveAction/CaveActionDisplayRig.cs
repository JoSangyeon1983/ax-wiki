using System.Collections.Generic;
using CellBig.EdgeBlending;
using CellBig.Module;
using UnityEngine;

public sealed class CaveActionDisplayRig : MonoBehaviour
{
    private readonly Dictionary<Camera, int> _originalCameraDisplays = new();
    private readonly Dictionary<Canvas, int> _originalCanvasDisplays = new();
    private CaveActionSettings _settings;
    private EdgeBlendingManager _edgeBlending;
    private bool _sessionActive;

    public Camera LeftCamera { get; private set; }
    public Camera FrontCamera { get; private set; }
    public Camera RightCamera { get; private set; }
    public Camera FloorCamera { get; private set; }

    public void Configure(CaveActionSettings settings)
    {
        _settings = settings;
        LeftCamera = FindCamera("LeftWallCamera");
        FrontCamera = FindCamera("FrontCamera");
        RightCamera = FindCamera("RightWallCamera");
        FloorCamera = FindCamera("FloorCamera");

        SetDisplay(LeftCamera, settings.LeftDisplay);
        SetDisplay(FrontCamera, settings.FrontDisplay);
        SetDisplay(RightCamera, settings.RightDisplay);
        SetDisplay(FloorCamera, settings.FloorDisplay);
        ActivateDisplay(settings.LeftDisplay);
        ActivateDisplay(settings.FrontDisplay);
        ActivateDisplay(settings.RightDisplay);
        ActivateDisplay(settings.FloorDisplay);

        _edgeBlending = FindObjectOfType<EdgeBlendingManager>();
        if (_edgeBlending != null)
        {
            _edgeBlending.SystemStarted -= OnEdgeBlendingStarted;
            _edgeBlending.SystemStarted += OnEdgeBlendingStarted;
            if (_edgeBlending.IsStarted)
            {
                ApplyFloorBlendDisplays();
            }
            else
            {
                EdgeBlendingErrorType result = _edgeBlending.StartSystem();
                if (result != EdgeBlendingErrorType.None)
                {
                    Debug.LogError(
                        $"[CaveActionDisplayRig] 엣지블렌딩 초기화에 실패했습니다: {result}");
                }
            }
        }

        KeepSingleAudioListener();
    }

    public void ActivateSession()
    {
        if (_sessionActive)
        {
            return;
        }

        foreach (UICamera uiCamera in FindObjectsOfType<UICamera>(true))
        {
            Redirect(uiCamera._Camera);
            Redirect(uiCamera._KioskCamera);
            Redirect(uiCamera._Canvas);
            Redirect(uiCamera._KioskCanvas);
        }
        _sessionActive = true;
    }

    public void DeactivateSession()
    {
        if (!_sessionActive)
        {
            return;
        }

        foreach (KeyValuePair<Camera, int> entry in _originalCameraDisplays)
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
        _sessionActive = false;
    }

    private Camera FindCamera(string cameraName)
    {
        foreach (Camera candidate in GetComponentsInChildren<Camera>(true))
        {
            if (candidate.name == cameraName)
            {
                return candidate;
            }
        }
        Debug.LogError($"[CaveActionDisplayRig] '{cameraName}' 카메라를 찾지 못했습니다.");
        return null;
    }

    private static void SetDisplay(Camera cameraComponent, int display)
    {
        if (cameraComponent != null)
        {
            cameraComponent.targetDisplay = Mathf.Max(0, display);
        }
    }

    private static void ActivateDisplay(int display)
    {
        if (!Application.isEditor && display > 0 && display < Display.displays.Length)
        {
            Display.displays[display].Activate();
        }
    }

    private void Redirect(Camera[] cameras)
    {
        if (cameras == null) return;
        foreach (Camera cameraComponent in cameras) Redirect(cameraComponent);
    }

    private void Redirect(Camera cameraComponent)
    {
        if (cameraComponent == null) return;
        if (!_originalCameraDisplays.ContainsKey(cameraComponent))
        {
            _originalCameraDisplays.Add(cameraComponent, cameraComponent.targetDisplay);
        }
        cameraComponent.targetDisplay = Mathf.Max(0, _settings.FrontDisplay);
    }

    private void Redirect(Canvas[] canvases)
    {
        if (canvases == null) return;
        foreach (Canvas canvas in canvases) Redirect(canvas);
    }

    private void Redirect(Canvas canvas)
    {
        if (canvas == null) return;
        if (!_originalCanvasDisplays.ContainsKey(canvas))
        {
            _originalCanvasDisplays.Add(canvas, canvas.targetDisplay);
        }
        canvas.targetDisplay = Mathf.Max(0, _settings.FrontDisplay);
    }

    private void OnEdgeBlendingStarted(EdgeBlendingSystemData _)
    {
        ApplyFloorBlendDisplays();
    }

    private void ApplyFloorBlendDisplays()
    {
        if (_settings?.FloorBlendDisplays == null || _edgeBlending?.EdgeBlenders == null)
        {
            return;
        }

        int count = Mathf.Min(_settings.FloorBlendDisplays.Length, _edgeBlending.EdgeBlenders.Count);
        for (int i = 0; i < count; i++)
        {
            EdgeBlender blender = _edgeBlending.EdgeBlenders[i];
            if (blender?.Camera == null) continue;

            int display = _settings.FloorBlendDisplays[i];
            blender.Camera.targetDisplay = Mathf.Max(0, display);
            blender.Camera.enabled = display != _settings.FrontDisplay;
            ActivateDisplay(display);
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

    private void OnDestroy()
    {
        if (_edgeBlending != null)
        {
            _edgeBlending.SystemStarted -= OnEdgeBlendingStarted;
        }
        DeactivateSession();
    }
}
