using System.Collections.Generic;
using CellBig.Module.OSCReceiver;
using UnityEngine;

public sealed class CaveBallFloorInteraction : MonoBehaviour
{
    private sealed class TrackedTouch
    {
        public Vector2 Position;
        public float LastSeenTime;
    }

    private readonly List<TrackedTouch> _activeTouches = new();
    private readonly List<LineRenderer> _debugRects = new();

    private CaveBall _ball;
    private CaveBallSetting _settings;
    private Camera _floorCamera;
    private Material _debugMaterial;
    private int _debugLayer;
    private bool _listening;
    private float _lastBounceTime = float.NegativeInfinity;

    public void Initialize(CaveBall ball, CaveBallSetting settings, Camera floorCamera)
    {
        _ball = ball;
        _settings = settings;
        _floorCamera = floorCamera;
        ConfigureDebugRendering();
    }

    public void StartListening()
    {
        if (_listening)
        {
            return;
        }

        Message.AddListener<OSCReceiverPointOutputMsg>(OnPointMessage);
        _listening = true;
    }

    public void StopListening()
    {
        if (_listening)
        {
            Message.RemoveListener<OSCReceiverPointOutputMsg>(OnPointMessage);
        }

        _listening = false;
        _activeTouches.Clear();
        UpdateDebugVisualization();
    }

    private void Update()
    {
        if (!_listening)
        {
            return;
        }

        RemoveExpiredTouches();

#if UNITY_EDITOR
        if (Input.GetMouseButton(0) && TryGetMouseFloorPoint(out Vector2 normalized))
        {
            UpdateTrackedTouch(normalized);
        }
#endif

        TryBounceFromActiveTouches();
        UpdateDebugVisualization();
    }

    private void OnDestroy()
    {
        StopListening();
        if (_debugMaterial != null)
        {
            Destroy(_debugMaterial);
        }
    }

    private void OnPointMessage(OSCReceiverPointOutputMsg message)
    {
        if (!_listening || message.sensorId != _settings.FloorSensorId || message.data == null)
        {
            return;
        }

        for (int i = 0; i < message.data.Count; i++)
        {
            UpdateTrackedTouch(NormalizeOscPoint(
                message.data[i],
                _settings.OscMinimum,
                _settings.OscMaximum,
                _settings.InvertOscX,
                _settings.InvertOscY));
        }
    }

    private void UpdateTrackedTouch(Vector2 normalized)
    {
        TrackedTouch nearest = null;
        float nearestDistance = _settings.FloorTouchMergeDistance;
        foreach (TrackedTouch touch in _activeTouches)
        {
            float distance = Vector2.Distance(touch.Position, normalized);
            if (distance <= nearestDistance)
            {
                nearestDistance = distance;
                nearest = touch;
            }
        }

        if (nearest == null)
        {
            nearest = new TrackedTouch();
            _activeTouches.Add(nearest);
        }

        nearest.Position = normalized;
        nearest.LastSeenTime = Time.unscaledTime;
    }

    private void RemoveExpiredTouches()
    {
        float now = Time.unscaledTime;
        for (int i = _activeTouches.Count - 1; i >= 0; i--)
        {
            if (now - _activeTouches[i].LastSeenTime > _settings.FloorContactHoldDuration)
            {
                _activeTouches.RemoveAt(i);
            }
        }
    }

    private void TryBounceFromActiveTouches()
    {
        if (_activeTouches.Count == 0 ||
            !IsBallNearFloor() ||
            Time.unscaledTime - _lastBounceTime < _settings.FloorBounceCooldown)
        {
            return;
        }

        Rect ballRect = GetBallFloorRect();
        Vector2 ballCenter = WorldToFloorNormalized(_ball.transform.position, _settings);
        float nearestDistance = float.PositiveInfinity;
        Vector2 nearestTouch = default;
        bool overlaps = false;

        foreach (TrackedTouch touch in _activeTouches)
        {
            if (!GetTouchRect(touch.Position).Overlaps(ballRect))
            {
                continue;
            }

            float distance = Vector2.Distance(touch.Position, ballCenter);
            if (distance < nearestDistance)
            {
                nearestDistance = distance;
                nearestTouch = touch.Position;
                overlaps = true;
            }
        }

        if (!overlaps)
        {
            return;
        }

        _ball.BounceFromFloorContact(ballCenter - nearestTouch);
        _lastBounceTime = Time.unscaledTime;
    }

    private Rect GetTouchRect(Vector2 touch)
    {
        float radius = _settings.FloorTouchViewportRadius;
        return Rect.MinMaxRect(
            touch.x - radius,
            touch.y - radius,
            touch.x + radius,
            touch.y + radius);
    }

    private Rect GetBallFloorRect()
    {
        SphereCollider ballCollider = _ball.GetComponent<SphereCollider>();
        if (ballCollider == null)
        {
            Vector2 point = WorldToFloorNormalized(_ball.transform.position, _settings);
            return new Rect(point.x, point.y, 0f, 0f);
        }

        Bounds bounds = ballCollider.bounds;
        Vector2 minimum = WorldToFloorNormalized(
            new Vector3(bounds.min.x, bounds.center.y, bounds.min.z),
            _settings);
        Vector2 maximum = WorldToFloorNormalized(
            new Vector3(bounds.max.x, bounds.center.y, bounds.max.z),
            _settings);
        return Rect.MinMaxRect(minimum.x, minimum.y, maximum.x, maximum.y);
    }

    private bool IsBallNearFloor()
    {
        float floorY = _settings.ArenaCenter.y - _settings.ArenaSize.y * 0.5f;
        return _ball.transform.position.y - floorY <= _settings.FloorHeightTolerance;
    }

    private bool TryGetMouseFloorPoint(out Vector2 normalized)
    {
        normalized = default;
        if (_floorCamera == null)
        {
            return false;
        }

        Ray ray = _floorCamera.ScreenPointToRay(Input.mousePosition);
        Plane floorPlane = new Plane(Vector3.up, new Vector3(0f, GetFloorY(), 0f));
        if (!floorPlane.Raycast(ray, out float enter))
        {
            return false;
        }

        normalized = WorldToFloorNormalized(ray.GetPoint(enter), _settings);
        return true;
    }

    private void ConfigureDebugRendering()
    {
        _debugLayer = LayerMask.NameToLayer("FloorDebug");
        if (_debugLayer < 0)
        {
            _debugLayer = 10;
        }

        int mask = 1 << _debugLayer;
        foreach (Camera cameraComponent in transform.root.GetComponentsInChildren<Camera>(true))
        {
            if (cameraComponent == _floorCamera)
            {
                cameraComponent.cullingMask |= mask;
            }
            else
            {
                cameraComponent.cullingMask &= ~mask;
            }
        }

        if (_settings.DebugMode)
        {
            Shader shader = Shader.Find("Sprites/Default");
            if (shader != null)
            {
                _debugMaterial = new Material(shader)
                {
                    name = "CaveBall Floor Touch Debug Material"
                };
            }
        }
    }

    private void UpdateDebugVisualization()
    {
        int visibleCount = _settings.DebugMode ? _activeTouches.Count : 0;
        while (_debugRects.Count < visibleCount)
        {
            _debugRects.Add(CreateDebugRect());
        }

        for (int i = 0; i < _debugRects.Count; i++)
        {
            bool visible = i < visibleCount;
            _debugRects[i].gameObject.SetActive(visible);
            if (visible)
            {
                SetDebugRectPositions(_debugRects[i], GetTouchRect(_activeTouches[i].Position));
            }
        }
    }

    private LineRenderer CreateDebugRect()
    {
        GameObject debugObject = new GameObject("Floor Touch Rect Debug");
        debugObject.layer = _debugLayer;
        debugObject.transform.SetParent(transform, false);

        LineRenderer line = debugObject.AddComponent<LineRenderer>();
        line.useWorldSpace = true;
        line.loop = false;
        line.positionCount = 5;
        line.startWidth = 0.06f;
        line.endWidth = 0.06f;
        line.startColor = Color.green;
        line.endColor = Color.green;
        line.sharedMaterial = _debugMaterial;
        return line;
    }

    private void SetDebugRectPositions(LineRenderer line, Rect rect)
    {
        float y = GetFloorY() + 0.15f;
        Vector3 bottomLeft = FloorNormalizedToWorld(new Vector2(rect.xMin, rect.yMin));
        Vector3 topLeft = FloorNormalizedToWorld(new Vector2(rect.xMin, rect.yMax));
        Vector3 topRight = FloorNormalizedToWorld(new Vector2(rect.xMax, rect.yMax));
        Vector3 bottomRight = FloorNormalizedToWorld(new Vector2(rect.xMax, rect.yMin));
        bottomLeft.y = topLeft.y = topRight.y = bottomRight.y = y;

        line.SetPositions(new[]
        {
            bottomLeft,
            topLeft,
            topRight,
            bottomRight,
            bottomLeft
        });
    }

    private Vector3 FloorNormalizedToWorld(Vector2 normalized)
    {
        return CaveBallRules.FloorNormalizedToWorld(
            normalized,
            _settings.ArenaCenter,
            _settings.ArenaSize);
    }

    private float GetFloorY()
    {
        return _settings.ArenaCenter.y - _settings.ArenaSize.y * 0.5f;
    }

    public static Vector2 NormalizeOscPoint(
        Vector2 raw,
        Vector2 minimum,
        Vector2 maximum,
        bool invertX,
        bool invertY)
    {
        return CaveBallRules.NormalizePoint(raw, minimum, maximum, invertX, invertY);
    }

    public static Vector2 WorldToFloorNormalized(Vector3 world, CaveBallSetting settings)
    {
        return CaveBallRules.WorldToFloorNormalized(
            world,
            settings.ArenaCenter,
            settings.ArenaSize);
    }
}
