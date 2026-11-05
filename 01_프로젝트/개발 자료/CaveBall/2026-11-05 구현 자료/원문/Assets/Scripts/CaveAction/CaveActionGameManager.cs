using System;
using System.Collections;
using System.Collections.Generic;
using CellBig;
using CellBig.Module.OSCReceiver;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public enum CaveActionPlayer
{
    Left,
    Right
}

public enum CaveActionAttackMode
{
    Jump,
    WallLaser,
    Hazard
}

public sealed class CaveActionGameManager : MonoBehaviour
{
    private static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");
    private static readonly int ColorId = Shader.PropertyToID("_Color");
    private static readonly int TintColorId = Shader.PropertyToID("_TintColor");

    private sealed class PlayerState
    {
        public CaveActionPlayer Side;
        public Image PlatformImage;
        public Rect PlatformRect;
        public Vector2 PlatformSize;
        public Vector2 TargetCenter;
        public Vector2 VisualCenter;
        public bool VisualInitialized;
        public bool HasPlatform;
        public bool EverDetected;
        public float LastDetectedTime = float.NegativeInfinity;
        public int Health;
        public float InvulnerableUntil;
        public float JumpInvulnerableUntil;
    }

    private sealed class TouchTrack
    {
        public Vector2 Position;
        public float LastSeen;
    }

    private sealed class HazardState
    {
        public Image Image;
        public Rect Rect;
        public Vector2 Size;
        public CaveActionPlayer Attacker;
        public CaveActionPlayer Defender;
    }

    private sealed class ScanLineState
    {
        public Image Image;
        public CaveActionPlayer Defender;
        public float StartedAt;
        public bool DefenderJumped;
    }

    private readonly List<TouchTrack> _leftWallTouches = new();
    private readonly List<TouchTrack> _rightWallTouches = new();
    private readonly List<TouchTrack> _frontWallTouches = new();
    private readonly List<HazardState> _hazards = new();
    private readonly List<ScanLineState> _scanLines = new();
    private readonly List<GameObject> _worldEffects = new();
    private readonly List<Vector2> _leftFloorPoints = new();
    private readonly List<Vector2> _rightFloorPoints = new();
    private readonly List<Vector2> _mouseRawPoints = new(1);
    private readonly List<float> _platformXScratch = new();
    private readonly List<float> _platformYScratch = new();
    private readonly List<Rect> _asteroidContactRects = new();
    private readonly List<CaveActionAttackMode> _attackModeBag = new(3);

    private CaveActionSettings _settings;
    private CaveActionDisplayRig _displayRig;
    private CaveActionSilhouetteController _silhouette;
    private CaveActionAsteroidController _asteroidController;
    private PlayerState _leftPlayer;
    private PlayerState _rightPlayer;
    private RectTransform _floorCanvas;
    private RectTransform _roleGuideRoot;
    private RectTransform _footPlatformsRoot;
    private RectTransform _hazardsRoot;
    private RectTransform _scanLinesRoot;
    private Image _platformTemplate;
    private Image _scanLineTemplate;
    private Image _hazardTemplate;
    private Transform _projectilesRoot;
    private Transform _worldEffectsRoot;
    private GameObject _laserTelegraphTemplate;
    private GameObject _redLaserBeamTemplate;
    private GameObject _blueLaserBeamTemplate;
    private GameObject _wallSpawnerTemplate;
    private GameObject _frontSpawnerTemplate;
    private GameObject _impactEffectTemplate;
    private GameObject _laserShooterTemplate;
    private Image _leftRolePanel;
    private Image _rightRolePanel;
    private TMP_Text _leftRoleText;
    private TMP_Text _rightRoleText;
    private RectTransform _turnAnnouncementRoot;
    private Image _turnAnnouncementPanel;
    private CanvasGroup _turnAnnouncementCanvasGroup;
    private TMP_Text _turnAnnouncementText;
    private int _lastRoleGuideSecond = -1;
    private int _lastCountdownSecond = -1;
    private int _worldEffectLayer;
    private int _frontEffectLayer;
    private int _floorEffectLayer;
    private CaveBallCameraShake _leftCameraShake;
    private CaveBallCameraShake _rightCameraShake;
    private CaveBallCameraShake _frontCameraShake;
    private CaveBallCameraShake _floorCameraShake;
    private CaveActionPlayer _attacker;
    private CaveActionAttackMode _attackMode;
    private CaveActionAttackMode? _lastAttackMode;
    private float _roundEndsAt;
    private bool _running;
    private bool _gameOver;
    private bool _listening;
    private Coroutine _restartCoroutine;
    private Coroutine _turnAnnouncementCoroutine;
    private int _attackGeneration;

#if UNITY_EDITOR
    private readonly Vector2[] _editorFloorPoints = new Vector2[2];
    private readonly bool[] _editorFloorPointActive = new bool[2];
#endif

    public CaveActionPlayer Attacker => _attacker;
    public CaveActionAttackMode AttackMode => _attackMode;
    public int LeftHealth => _leftPlayer?.Health ?? 0;
    public int RightHealth => _rightPlayer?.Health ?? 0;

    public bool Initialize(CaveActionSettings settings, CaveActionDisplayRig displayRig)
    {
        _settings = settings;
        _displayRig = displayRig;
        _floorCanvas = FindDeepComponent<Canvas>("Canvas", displayRig.FloorCamera?.transform)?.transform as RectTransform;
        _footPlatformsRoot = FindDeepTransform("FootPlatforms") as RectTransform;
        _hazardsRoot = FindDeepTransform("FloorHazards") as RectTransform;
        _scanLinesRoot = FindDeepTransform("ScanLines") as RectTransform;
        _platformTemplate = FindDeepComponent<Image>("FootPlatformTemplate");
        _scanLineTemplate = FindDeepComponent<Image>("ScanLineTemplate");
        _hazardTemplate = FindDeepComponent<Image>("FloorHazardTemplate");
        _projectilesRoot = FindDeepTransform("Projectiles");
        _laserTelegraphTemplate = FindDeepTransform("LaserTelegraphTemplate")?.gameObject;
        _redLaserBeamTemplate = FindDeepTransform("RedLaserBeamTemplate")?.gameObject;
        _blueLaserBeamTemplate = FindDeepTransform("BlueLaserBeamTemplate")?.gameObject;
        _wallSpawnerTemplate = FindDeepTransform("WallSpawnerTemplate")?.gameObject;
        _frontSpawnerTemplate = FindDeepTransform("FrontSpawnerTemplate")?.gameObject;
        _impactEffectTemplate = FindDeepTransform("ImpactEffectTemplate")?.gameObject;
        _laserShooterTemplate = FindDeepTransform("LaserShooterTemplate")?.gameObject;
        GameObject asteroidBreakTemplate =
            FindDeepTransform("AsteroidBreakTemplate")?.gameObject;
        Transform asteroidWall = FindDeepTransform("AsteroidWall");
        GameObject[] bigAsteroidTemplates = FindTemplates(
            "BigAsteroidTemplateA",
            "BigAsteroidTemplateB",
            "BigAsteroidTemplateC");
        GameObject[] midAsteroidTemplates = FindTemplates(
            "MidAsteroidTemplateA",
            "MidAsteroidTemplateB",
            "MidAsteroidTemplateC");
        GameObject[] smallAsteroidTemplates = FindTemplates(
            "SmallAsteroidTemplateA",
            "SmallAsteroidTemplateB",
            "SmallAsteroidTemplateC");
        _worldEffectLayer = LayerMask.NameToLayer("UIEffect");
        if (_worldEffectLayer < 0) _worldEffectLayer = 9;
        _frontEffectLayer = LayerMask.NameToLayer("CaveActionFrontFX");
        _floorEffectLayer = LayerMask.NameToLayer("CaveActionFloorFX");

        if (_floorCanvas == null || _footPlatformsRoot == null || _hazardsRoot == null ||
            _scanLinesRoot == null || _platformTemplate == null || _scanLineTemplate == null ||
            _hazardTemplate == null || _projectilesRoot == null ||
            _laserTelegraphTemplate == null ||
            _redLaserBeamTemplate == null || _blueLaserBeamTemplate == null ||
            _wallSpawnerTemplate == null || _frontSpawnerTemplate == null ||
            _impactEffectTemplate == null || _laserShooterTemplate == null ||
            asteroidBreakTemplate == null || asteroidWall == null ||
            ContainsNull(bigAsteroidTemplates) ||
            ContainsNull(midAsteroidTemplates) ||
            ContainsNull(smallAsteroidTemplates) ||
            _frontEffectLayer < 0 || _floorEffectLayer < 0)
        {
            Debug.LogError("[CaveAction] CaveActionBG의 필수 게임 오브젝트를 찾지 못했습니다.");
            return false;
        }
        ConfigureEffectCameraLayers();

        GameObject effectsRoot = new("Attack Effect Instances");
        effectsRoot.transform.SetParent(transform, false);
        _worldEffectsRoot = effectsRoot.transform;
        _asteroidController = gameObject.AddComponent<CaveActionAsteroidController>();
        if (!_asteroidController.Initialize(
                settings,
                asteroidWall,
                bigAsteroidTemplates,
                midAsteroidTemplates,
                smallAsteroidTemplates,
                asteroidBreakTemplate,
                _floorEffectLayer))
        {
            return false;
        }

        _leftPlayer = CreatePlayer(CaveActionPlayer.Left);
        _rightPlayer = CreatePlayer(CaveActionPlayer.Right);
        _silhouette = gameObject.AddComponent<CaveActionSilhouetteController>();
        if (!_silhouette.Initialize(settings))
        {
            return false;
        }
        if (!BindRoleGuide())
        {
            Debug.LogError("[CaveAction] CaveActionBG에서 RoleGuide UI를 찾지 못했습니다.");
            return false;
        }
        _leftCameraShake = GetOrAddCameraShake(_displayRig.LeftCamera);
        _rightCameraShake = GetOrAddCameraShake(_displayRig.RightCamera);
        _frontCameraShake = GetOrAddCameraShake(_displayRig.FrontCamera);
        _floorCameraShake = GetOrAddCameraShake(_displayRig.FloorCamera);

        SoundManager.Instance.PlaySound(SoundType.ArcadeGameBGM3_Loop);

        return true;
    }

    public void StartGame()
    {
        if (_running || _leftPlayer == null) return;
        if (_settings.UseOSC)
        {
            RegisterInput();
        }
        _silhouette?.StartSession();
        ResetGame();
#if UNITY_EDITOR
        if (_settings.EnableEditorMouseInput)
        {
            Debug.Log(
                "[CaveAction Editor Test] 좌/우 클릭 유지: 발판, " +
                "Shift+좌클릭 또는 O: 정면 공격, Ctrl+좌클릭 또는 P: 측벽 공격");
        }
#endif
        if (!_settings.UseOSC)
        {
            Debug.Log("[CaveAction] OSC 비활성화: 멀티 디스플레이 마우스 입력을 사용합니다.");
        }
        else if (_settings.UseOSCForFloorOnly)
        {
            Debug.Log("[CaveAction] 혼합 입력: 바닥은 OSC, 벽면은 멀티 디스플레이 마우스를 사용합니다.");
        }
    }

    public void StopGame()
    {
        _running = false;
        _gameOver = false;
        if (_restartCoroutine != null)
        {
            StopCoroutine(_restartCoroutine);
            _restartCoroutine = null;
        }
        if (_turnAnnouncementCoroutine != null)
        {
            StopCoroutine(_turnAnnouncementCoroutine);
            _turnAnnouncementCoroutine = null;
        }
        UnregisterInput();
        ClearAttacks();
        _asteroidController?.StopSession();
        _silhouette?.StopSession();
        SetPlatformVisible(_leftPlayer, false);
        SetPlatformVisible(_rightPlayer, false);
#if UNITY_EDITOR
        Array.Clear(_editorFloorPointActive, 0, _editorFloorPointActive.Length);
#endif
        _mouseRawPoints.Clear();
        if (_roleGuideRoot != null) _roleGuideRoot.gameObject.SetActive(false);
        if (_turnAnnouncementRoot != null) _turnAnnouncementRoot.gameObject.SetActive(false);
    }

    private void Update()
    {
        if (!_running || _gameOver) return;

#if UNITY_EDITOR
        if (_settings.EnableEditorMouseInput)
        {
            ProcessEditorKeyboardShortcuts();
        }
        if (_settings.EnableEditorMouseInput && _settings.UseOSC && !_settings.UseOSCForFloorOnly)
        {
            ProcessEditorMouseInput();
        }
#endif
        if (!_settings.UseOSC || _settings.UseOSCForFloorOnly)
        {
            ProcessDisplayMouseInput();
        }

        UpdatePlatformLoss(_leftPlayer);
        UpdatePlatformLoss(_rightPlayer);
        UpdatePlatformVisual(_leftPlayer);
        UpdatePlatformVisual(_rightPlayer);
        UpdateHazards();
        UpdateAsteroidContacts();
        UpdateScanLines();
        UpdateRoleGuide();
        RemoveExpiredTracks(_leftWallTouches);
        RemoveExpiredTracks(_rightWallTouches);
        RemoveExpiredTracks(_frontWallTouches);

        if (Time.unscaledTime >= _roundEndsAt)
        {
            SwitchRoles();
        }
    }

    private void ResetGame()
    {
        ClearAttacks();
        _gameOver = false;
        _running = true;
        ResetPlayer(_leftPlayer);
        ResetPlayer(_rightPlayer);
        _asteroidController?.ResetSession();
        _attacker = UnityEngine.Random.value < 0.5f ? CaveActionPlayer.Left : CaveActionPlayer.Right;
        ResetAttackModeBag();
        SelectAttackMode();
        _roundEndsAt = Time.unscaledTime + Mathf.Max(1f, _settings.AttackDuration);
        _silhouette?.ResetVisuals();
        UpdatePlatformColors();
        RefreshRoleGuide();
        AnnounceTurn();
#if UNITY_EDITOR
        if (_settings.EnableEditorMouseInput)
        {
            Debug.Log($"[CaveAction Editor Test] {_attacker} 플레이어 공격 시작");
        }
#endif
    }

    private void ResetPlayer(PlayerState player)
    {
        player.Health = Mathf.Max(1, _settings.PlatformHealth);
        player.InvulnerableUntil = float.NegativeInfinity;
        player.JumpInvulnerableUntil = float.NegativeInfinity;
        player.HasPlatform = false;
        player.EverDetected = false;
        player.VisualInitialized = false;
        player.LastDetectedTime = float.NegativeInfinity;
        SetPlatformVisible(player, false);
    }

    private PlayerState CreatePlayer(CaveActionPlayer side)
    {
        Image image = Instantiate(_platformTemplate, _footPlatformsRoot);
        image.name = side == CaveActionPlayer.Left ? "Left Player Platform" : "Right Player Platform";
        image.raycastTarget = false;
        image.gameObject.SetActive(false);
        return new PlayerState
        {
            Side = side,
            PlatformImage = image,
            Health = Mathf.Max(1, _settings.PlatformHealth)
        };
    }

    private void SelectAttackMode()
    {
        if (_attackModeBag.Count == 0)
        {
            RefillAttackModeBag();
        }

        int index = _attackModeBag.Count - 1;
        _attackMode = _attackModeBag[index];
        _attackModeBag.RemoveAt(index);
        _lastAttackMode = _attackMode;
        _lastCountdownSecond = -1;
        if (_attackMode == CaveActionAttackMode.Hazard)
        {
            SpawnHazard(GetPlayer(_attacker));
        }
    }

    private void ResetAttackModeBag()
    {
        _attackModeBag.Clear();
        _lastAttackMode = null;
    }

    private void RefillAttackModeBag()
    {
        _attackModeBag.Clear();
        _attackModeBag.Add(CaveActionAttackMode.Jump);
        _attackModeBag.Add(CaveActionAttackMode.WallLaser);
        _attackModeBag.Add(CaveActionAttackMode.Hazard);

        for (int i = _attackModeBag.Count - 1; i > 0; i--)
        {
            int swapIndex = UnityEngine.Random.Range(0, i + 1);
            (_attackModeBag[i], _attackModeBag[swapIndex]) =
                (_attackModeBag[swapIndex], _attackModeBag[i]);
        }

        int nextIndex = _attackModeBag.Count - 1;
        if (_lastAttackMode.HasValue &&
            _attackModeBag[nextIndex] == _lastAttackMode.Value)
        {
            int swapIndex = UnityEngine.Random.Range(0, nextIndex);
            (_attackModeBag[nextIndex], _attackModeBag[swapIndex]) =
                (_attackModeBag[swapIndex], _attackModeBag[nextIndex]);
        }
    }

    private bool BindRoleGuide()
    {
        _roleGuideRoot = FindDeepTransform("RoleGuide") as RectTransform;
        if (_roleGuideRoot == null) return false;

        _leftRolePanel = FindDeepComponent<Image>("LeftRole", _roleGuideRoot);
        _rightRolePanel = FindDeepComponent<Image>("RightRole", _roleGuideRoot);
        _leftRoleText = _leftRolePanel != null
            ? FindDeepComponent<TMP_Text>("Label", _leftRolePanel.transform)
            : null;
        _rightRoleText = _rightRolePanel != null
            ? FindDeepComponent<TMP_Text>("Label", _rightRolePanel.transform)
            : null;
        _turnAnnouncementRoot = FindDeepTransform("TurnAnnouncement") as RectTransform;
        _turnAnnouncementPanel = _turnAnnouncementRoot != null
            ? _turnAnnouncementRoot.GetComponent<Image>()
            : null;
        _turnAnnouncementCanvasGroup = _turnAnnouncementRoot != null
            ? _turnAnnouncementRoot.GetComponent<CanvasGroup>()
            : null;
        _turnAnnouncementText = _turnAnnouncementRoot != null
            ? FindDeepComponent<TMP_Text>("Label", _turnAnnouncementRoot)
            : null;
        return _leftRolePanel != null && _rightRolePanel != null &&
               _leftRoleText != null && _rightRoleText != null &&
               _turnAnnouncementPanel != null &&
               _turnAnnouncementCanvasGroup != null &&
               _turnAnnouncementText != null;
    }

    private void RefreshRoleGuide()
    {
        _lastRoleGuideSecond = -1;
        UpdateRoleGuide();
    }

    private void UpdateRoleGuide()
    {
        if (_roleGuideRoot == null || _gameOver || !_running) return;
        if (!_roleGuideRoot.gameObject.activeSelf) _roleGuideRoot.gameObject.SetActive(true);

        float pulse = 0.78f + Mathf.PingPong(Time.unscaledTime * 1.8f, 0.18f);
        SetRolePanelColor(_leftRolePanel, CaveActionPlayer.Left, pulse);
        SetRolePanelColor(_rightRolePanel, CaveActionPlayer.Right, pulse);

        int remaining = Mathf.Max(0, Mathf.CeilToInt(_roundEndsAt - Time.unscaledTime));
        if (remaining > 0 && remaining <= 3 && remaining != _lastCountdownSecond)
        {
            _lastCountdownSecond = remaining;
            ShowAnnouncement(
                remaining.ToString(),
                GetPlayerColor(_attacker),
                _settings.CountdownAnnouncementDuration,
                SoundType.Explosion_Electro01);
        }
        if (remaining == _lastRoleGuideSecond) return;
        _lastRoleGuideSecond = remaining;

        string modeLabel = GetAttackModeLabel();
        _leftRoleText.text = _attacker == CaveActionPlayer.Left
            ? $"ATTACK: {modeLabel}  {remaining}s  |  HP {_leftPlayer.Health}"
            : $"DEFENSE  |  HP {_leftPlayer.Health}";
        _rightRoleText.text = _attacker == CaveActionPlayer.Right
            ? $"ATTACK: {modeLabel}  {remaining}s  |  HP {_rightPlayer.Health}"
            : $"DEFENSE  |  HP {_rightPlayer.Health}";
    }

    private string GetAttackModeLabel()
    {
        return _attackMode switch
        {
            CaveActionAttackMode.Jump => "JUMP",
            CaveActionAttackMode.WallLaser => "WALL LASER",
            CaveActionAttackMode.Hazard => "HAZARD",
            _ => string.Empty
        };
    }

    private void AnnounceTurn()
    {
        string text =
            $"{(_attacker == CaveActionPlayer.Left ? "RED" : "BLUE")} PLAYER ATTACK\n" +
            GetAttackModeLabel();
        ShowAnnouncement(
            text,
            GetPlayerColor(_attacker),
            _settings.TurnAnnouncementDuration,
            GetAttackModeSound());
    }

    private SoundType GetAttackModeSound()
    {
        return _attackMode switch
        {
            CaveActionAttackMode.Jump => SoundType.StartWave_Electro02,
            CaveActionAttackMode.WallLaser => SoundType.StartWave_ArcaneEnergyPlasma03,
            CaveActionAttackMode.Hazard => SoundType.StartWave_FireBlazing03,
            _ => SoundType.StartWave_ArcaneEnergyPlasma01
        };
    }

    private void ShowAnnouncement(
        string text,
        Color color,
        float duration,
        SoundType sound)
    {
        if (_turnAnnouncementRoot == null) return;
        if (_turnAnnouncementCoroutine != null)
        {
            StopCoroutine(_turnAnnouncementCoroutine);
        }
        if (sound != SoundType.None)
        {
            SoundManager.Instance.PlaySound(sound);
        }
        _turnAnnouncementCoroutine = StartCoroutine(
            PlayAnnouncement(text, color, duration));
    }

    private IEnumerator PlayAnnouncement(string text, Color color, float requestedDuration)
    {
        Color panelColor = color;
        panelColor.a = 0.92f;
        _turnAnnouncementPanel.color = panelColor;
        _turnAnnouncementText.text = text;
        _turnAnnouncementRoot.localScale = Vector3.one * 1.12f;
        _turnAnnouncementCanvasGroup.alpha = 0f;
        _turnAnnouncementRoot.gameObject.SetActive(true);

        float duration = Mathf.Max(0.2f, requestedDuration);
        float startedAt = Time.unscaledTime;
        while (Time.unscaledTime - startedAt < duration)
        {
            float progress = Mathf.Clamp01((Time.unscaledTime - startedAt) / duration);
            float fadeIn = Mathf.Clamp01(progress / 0.15f);
            float fadeOut = Mathf.Clamp01((1f - progress) / 0.3f);
            _turnAnnouncementCanvasGroup.alpha = Mathf.Min(fadeIn, fadeOut);
            float scale = Mathf.Lerp(1.12f, 1f, Mathf.SmoothStep(0f, 1f, progress));
            _turnAnnouncementRoot.localScale = Vector3.one * scale;
            yield return null;
        }

        _turnAnnouncementCanvasGroup.alpha = 0f;
        _turnAnnouncementRoot.gameObject.SetActive(false);
        _turnAnnouncementCoroutine = null;
    }

    private void SetRolePanelColor(Image panel, CaveActionPlayer side, float attackerAlpha)
    {
        if (panel == null) return;
        Color color = GetPlayerColor(side);
        color.a = side == _attacker ? attackerAlpha : 0.28f;
        panel.color = color;
    }

    private void RegisterInput()
    {
        if (_listening) return;
        Message.AddListener<OSCReceiverPointOutputMsg>(OnPointMessage);
        _listening = true;
    }

    private void UnregisterInput()
    {
        if (!_listening) return;
        Message.RemoveListener<OSCReceiverPointOutputMsg>(OnPointMessage);
        _listening = false;
    }

    private void OnPointMessage(OSCReceiverPointOutputMsg message)
    {
        if (!_running || _gameOver || message == null) return;

        if (message.sensorId == _settings.FloorSensor.SensorId)
        {
            ProcessFloorInput(message.data);
        }
        else if (_settings.UseOSCForFloorOnly)
        {
            return;
        }
        else if (message.sensorId == _settings.LeftWallSensor.SensorId)
        {
            ProcessWallInput(message.data, _settings.LeftWallSensor, CaveActionSurface.LeftWall);
        }
        else if (message.sensorId == _settings.RightWallSensor.SensorId)
        {
            ProcessWallInput(message.data, _settings.RightWallSensor, CaveActionSurface.RightWall);
        }
        else if (message.sensorId == _settings.FrontWallSensor.SensorId)
        {
            ProcessWallInput(message.data, _settings.FrontWallSensor, CaveActionSurface.FrontWall);
        }
    }

    private void ProcessFloorInput(List<Vector2> rawPoints)
    {
        _leftFloorPoints.Clear();
        _rightFloorPoints.Clear();
        if (rawPoints != null)
        {
            foreach (Vector2 raw in rawPoints)
            {
                Vector2 point = Normalize(raw, _settings.FloorSensor);
                if (point.x < 0.5f) _leftFloorPoints.Add(point);
                else _rightFloorPoints.Add(point);
            }
        }

        UpdatePlayerPlatform(_leftPlayer, _leftFloorPoints);
        UpdatePlayerPlatform(_rightPlayer, _rightFloorPoints);
    }

    private void ProcessDisplayMouseInput()
    {
        bool floorHeld = Input.GetMouseButton(0);
        if (!floorHeld && !Input.GetMouseButtonDown(0)) return;

        Vector3 relative = Display.RelativeMouseAt(Input.mousePosition);
        int displayIndex = Mathf.RoundToInt(relative.z);
        Vector2 displayPosition = new(relative.x, relative.y);
        if (relative == Vector3.zero)
        {
            displayIndex = 0;
            displayPosition = Input.mousePosition;
        }

        if (displayIndex < 0 || displayIndex >= Display.displays.Length) return;
        Display display = Display.displays[displayIndex];
        Vector2 normalized = new(
            Mathf.Clamp01(displayPosition.x / Mathf.Max(1f, display.renderingWidth)),
            Mathf.Clamp01(displayPosition.y / Mathf.Max(1f, display.renderingHeight)));

        if (TryGetFloorPosition(displayIndex, normalized, out Vector2 floorPosition))
        {
            if (!_settings.UseOSC && floorHeld) ProcessMouseFloorPoint(floorPosition);
            return;
        }

        if (!Input.GetMouseButtonDown(0)) return;
        if (displayIndex == _settings.LeftDisplay)
        {
            ProcessMouseWallPoint(normalized, _settings.LeftWallSensor, CaveActionSurface.LeftWall);
        }
        else if (displayIndex == _settings.RightDisplay)
        {
            ProcessMouseWallPoint(normalized, _settings.RightWallSensor, CaveActionSurface.RightWall);
        }
        else if (displayIndex == _settings.FrontDisplay)
        {
            ProcessMouseWallPoint(normalized, _settings.FrontWallSensor, CaveActionSurface.FrontWall);
        }
    }

    private bool TryGetFloorPosition(int displayIndex, Vector2 normalized, out Vector2 floorPosition)
    {
        if (displayIndex == _settings.FloorDisplay)
        {
            floorPosition = normalized;
            return true;
        }

        int blendIndex = _settings.FloorBlendDisplays == null
            ? -1
            : Array.IndexOf(_settings.FloorBlendDisplays, displayIndex);
        if (blendIndex < 0)
        {
            floorPosition = default;
            return false;
        }

        int count = _settings.FloorBlendDisplays.Length;
        floorPosition = new Vector2(
            normalized.x,
            (count - 1 - blendIndex + normalized.y) / count);
        return true;
    }

    private void ProcessMouseFloorPoint(Vector2 normalized)
    {
        _mouseRawPoints.Clear();
        _mouseRawPoints.Add(Denormalize(normalized, _settings.FloorSensor));
        ProcessFloorInput(_mouseRawPoints);
    }

    private void ProcessMouseWallPoint(
        Vector2 normalized,
        CaveActionSensorCalibration calibration,
        CaveActionSurface surface)
    {
        _mouseRawPoints.Clear();
        _mouseRawPoints.Add(Denormalize(normalized, calibration));
        ProcessWallInput(_mouseRawPoints, calibration, surface);
    }

    private static Vector2 Denormalize(
        Vector2 normalized,
        CaveActionSensorCalibration calibration)
    {
        if (calibration.InvertX) normalized.x = 1f - normalized.x;
        if (calibration.InvertY) normalized.y = 1f - normalized.y;
        return new Vector2(
            Mathf.Lerp(calibration.Minimum.x, calibration.Maximum.x, normalized.x),
            Mathf.Lerp(calibration.Minimum.y, calibration.Maximum.y, normalized.y));
    }

#if UNITY_EDITOR
    private void ProcessEditorKeyboardShortcuts()
    {
        if (Input.GetKeyDown(KeyCode.O))
        {
            Vector2 frontCenter = new(
                _attacker == CaveActionPlayer.Left ? 0.25f : 0.75f,
                0.5f);
            StartLaserAttack(_attacker, CaveActionSurface.FrontWall, frontCenter);
        }
        if (Input.GetKeyDown(KeyCode.P))
        {
            CaveActionSurface sideSurface = _attacker == CaveActionPlayer.Left
                ? CaveActionSurface.LeftWall
                : CaveActionSurface.RightWall;
            StartLaserAttack(_attacker, sideSurface, new Vector2(0.5f, 0.5f));
        }
    }

    private void ProcessEditorMouseInput()
    {
        bool frontAttack = Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift);
        bool sideAttack = Input.GetKey(KeyCode.LeftControl) || Input.GetKey(KeyCode.RightControl);
        Vector2 normalizedMouse = GetEditorNormalizedMouse();

        if (Input.GetMouseButtonDown(0) && (frontAttack || sideAttack))
        {
            if (sideAttack)
            {
                CaveActionSurface surface = _attacker == CaveActionPlayer.Left
                    ? CaveActionSurface.LeftWall
                    : CaveActionSurface.RightWall;
                StartLaserAttack(_attacker, surface, normalizedMouse);
            }
            else
            {
                normalizedMouse.x = _attacker == CaveActionPlayer.Left
                    ? normalizedMouse.x * 0.5f
                    : 0.5f + normalizedMouse.x * 0.5f;
                StartLaserAttack(_attacker, CaveActionSurface.FrontWall, normalizedMouse);
            }
        }
        else
        {
            for (int button = 0; button < _editorFloorPointActive.Length; button++)
            {
                if (Input.GetMouseButtonDown(button))
                {
                    _editorFloorPointActive[button] = true;
                    _editorFloorPoints[button] = normalizedMouse;
                }
            }
        }

        for (int button = 0; button < _editorFloorPointActive.Length; button++)
        {
            if (Input.GetMouseButtonUp(button))
            {
                _editorFloorPointActive[button] = false;
            }
        }

        _mouseRawPoints.Clear();
        for (int i = 0; i < _editorFloorPointActive.Length; i++)
        {
            if (_editorFloorPointActive[i])
            {
                _mouseRawPoints.Add(Denormalize(
                    _editorFloorPoints[i],
                    _settings.FloorSensor));
            }
        }
        if (_mouseRawPoints.Count > 0)
        {
            ProcessFloorInput(_mouseRawPoints);
        }
    }

    private static Vector2 GetEditorNormalizedMouse()
    {
        return new Vector2(
            Mathf.Clamp01(Input.mousePosition.x / Mathf.Max(1f, Screen.width)),
            Mathf.Clamp01(Input.mousePosition.y / Mathf.Max(1f, Screen.height)));
    }

#endif

    private void UpdatePlayerPlatform(PlayerState player, List<Vector2> points)
    {
        if (points.Count == 0) return;

        bool wasMissing = !player.HasPlatform &&
                          player.EverDetected &&
                          Time.unscaledTime - player.LastDetectedTime > _settings.JumpDetectionDelay;
        Rect measuredRect = CaveActionRules.CalculateFixedPlatformRect(
            points,
            player.Side == CaveActionPlayer.Left,
            _settings.PlatformFixedSize,
            _platformXScratch,
            _platformYScratch);
        Vector2 measuredCenter = measuredRect.center;
        player.PlatformSize = measuredRect.size;
        if (!player.VisualInitialized)
        {
            player.VisualCenter = measuredCenter;
            player.TargetCenter = measuredCenter;
            player.VisualInitialized = true;
        }
        else if (Vector2.Distance(player.TargetCenter, measuredCenter) >= _settings.PlatformInputDeadZone)
        {
            player.TargetCenter = measuredCenter;
        }
        player.PlatformRect = new Rect(
            player.VisualCenter - measuredRect.size * 0.5f,
            measuredRect.size);
        player.LastDetectedTime = Time.unscaledTime;
        player.HasPlatform = true;
        if (!wasMissing)
        {
            ApplyPlatformRect(player);
        }
        SetPlatformVisible(player, true);

        player.EverDetected = true;
    }

    private void UpdatePlatformLoss(PlayerState player)
    {
        if (!player.HasPlatform || !player.EverDetected) return;
        if (Time.unscaledTime - player.LastDetectedTime <= _settings.JumpDetectionDelay) return;

        player.HasPlatform = false;
        player.JumpInvulnerableUntil = Mathf.Max(
            player.JumpInvulnerableUntil,
            Time.unscaledTime + Mathf.Max(0f, _settings.JumpInvulnerabilityDuration));
        SetPlatformVisible(player, false);
        if (player.Side == _attacker && _attackMode == CaveActionAttackMode.Jump)
        {
            SpawnScanLine(Opposite(player.Side));
        }
    }

    private void UpdatePlatformVisual(PlayerState player)
    {
        if (!player.HasPlatform || !player.VisualInitialized) return;

        float sharpness = Mathf.Max(0.01f, _settings.PlatformFollowSharpness);
        float interpolation = 1f - Mathf.Exp(-sharpness * Time.unscaledDeltaTime);
        Vector2 smoothedTarget = Vector2.Lerp(
            player.VisualCenter,
            player.TargetCenter,
            interpolation);
        float maximumStep = Mathf.Max(0.01f, _settings.PlatformMaximumFollowSpeed) *
                            Time.unscaledDeltaTime;
        player.VisualCenter = Vector2.MoveTowards(
            player.VisualCenter,
            smoothedTarget,
            maximumStep);
        player.PlatformRect = new Rect(
            player.VisualCenter - player.PlatformSize * 0.5f,
            player.PlatformSize);
        ApplyPlatformRect(player);
    }

    private void ApplyPlatformRect(PlayerState player)
    {
        Rect canvasRect = _floorCanvas.rect;
        RectTransform rect = player.PlatformImage.rectTransform;
        rect.anchorMin = rect.anchorMax = new Vector2(0.5f, 0.5f);
        rect.sizeDelta = new Vector2(
            player.PlatformRect.width * canvasRect.width,
            player.PlatformRect.height * canvasRect.height);
        rect.anchoredPosition = new Vector2(
            (player.PlatformRect.center.x - 0.5f) * canvasRect.width,
            (player.PlatformRect.center.y - 0.5f) * canvasRect.height);
    }

    private void ProcessWallInput(
        List<Vector2> rawPoints,
        CaveActionSensorCalibration calibration,
        CaveActionSurface surface)
    {
        if (rawPoints == null || rawPoints.Count == 0) return;
        if (_attackMode != CaveActionAttackMode.WallLaser) return;
        if (surface == CaveActionSurface.LeftWall && _attacker != CaveActionPlayer.Left) return;
        if (surface == CaveActionSurface.RightWall && _attacker != CaveActionPlayer.Right) return;

        List<TouchTrack> tracks = surface switch
        {
            CaveActionSurface.LeftWall => _leftWallTouches,
            CaveActionSurface.RightWall => _rightWallTouches,
            _ => _frontWallTouches
        };

        foreach (Vector2 raw in rawPoints)
        {
            Vector2 point = Normalize(raw, calibration);
            if (surface == CaveActionSurface.FrontWall)
            {
                bool belongsToAttacker = _attacker == CaveActionPlayer.Left ? point.x < 0.5f : point.x >= 0.5f;
                if (!belongsToAttacker) continue;
            }
            TrackTouchAndAttack(tracks, point, surface);
        }
    }

    private void TrackTouchAndAttack(List<TouchTrack> tracks, Vector2 point, CaveActionSurface surface)
    {
        TouchTrack nearest = null;
        float nearestDistance = _settings.TouchMergeDistance;
        foreach (TouchTrack track in tracks)
        {
            float distance = Vector2.Distance(track.Position, point);
            if (distance <= nearestDistance)
            {
                nearest = track;
                nearestDistance = distance;
            }
        }

        bool isNew = nearest == null ||
                     Time.unscaledTime - nearest.LastSeen > _settings.TouchAttackCooldown;
        if (nearest == null)
        {
            nearest = new TouchTrack();
            tracks.Add(nearest);
        }
        nearest.Position = point;
        nearest.LastSeen = Time.unscaledTime;
        if (isNew) StartLaserAttack(_attacker, surface, point);
    }

    private void RemoveExpiredTracks(List<TouchTrack> tracks)
    {
        for (int i = tracks.Count - 1; i >= 0; i--)
        {
            if (Time.unscaledTime - tracks[i].LastSeen > _settings.ContactHoldDuration)
            {
                tracks.RemoveAt(i);
            }
        }
    }

    private void StartLaserAttack(CaveActionPlayer attacker, CaveActionSurface surface, Vector2 touch)
    {
        if (_attackMode != CaveActionAttackMode.WallLaser) return;

        PlayerState defender = GetPlayer(Opposite(attacker));
        Vector2 targetPoint = defender.HasPlatform
            ? defender.PlatformRect.center
            : new Vector2(defender.Side == CaveActionPlayer.Left ? 0.25f : 0.75f, 0.5f);
        Vector3 start = SurfaceToWorld(surface, touch);
        Vector3 target = FloorToWorld(targetPoint);
        Vector3 inwardNormal = GetSurfaceInwardNormal(surface);
        start += inwardNormal * Mathf.Max(0f, _settings.WorldEffectSurfaceOffset);
        Vector3[] laserPath = BuildLaserPath(surface, start, target);
        bool crossesFrontFloor = surface == CaveActionSurface.FrontWall;
        int effectLayer = crossesFrontFloor ? _frontEffectLayer : _worldEffectLayer;
        GameObject shooter = CreateLaserShooter(
            attacker,
            surface,
            touch,
            inwardNormal,
            effectLayer);

        int generation = _attackGeneration;
        StartCoroutine(RunLaserAttack(
            generation,
            attacker,
            defender,
            targetPoint,
            target,
            laserPath,
            crossesFrontFloor,
            surface,
            touch,
            start,
            inwardNormal,
            effectLayer,
            shooter));
    }

    private GameObject CreateLaserShooter(
        CaveActionPlayer attacker,
        CaveActionSurface surface,
        Vector2 touch,
        Vector3 inwardNormal,
        int effectLayer)
    {
        float margin = Mathf.Max(0.01f, _settings.LaserShooterOffscreenMargin);
        Vector2 offscreenTouch = touch;
        offscreenTouch.x = touch.x < 0.5f ? -margin : 1f + margin;
        Vector3 offscreenPosition = SurfaceToWorld(surface, offscreenTouch) +
                                    inwardNormal * Mathf.Max(0f, _settings.WorldEffectSurfaceOffset);

        GameObject instance = Instantiate(_laserShooterTemplate, _worldEffectsRoot);
        instance.name = $"{attacker} Laser Shooter";
        SetLayerRecursively(instance.transform, effectLayer);
        instance.transform.position = offscreenPosition;
        foreach (Collider collider in instance.GetComponentsInChildren<Collider>(true))
        {
            collider.enabled = false;
        }
        ApplyEffectColor(instance, GetPlayerColor(attacker));
        instance.SetActive(true);
        PlayEffectComponents(instance);
        _worldEffects.Add(instance);
        return instance;
    }

    private Vector3[] BuildLaserPath(
        CaveActionSurface surface,
        Vector3 start,
        Vector3 target)
    {
        if (surface != CaveActionSurface.FrontWall)
        {
            return new[] { start, target };
        }

        Camera frontCamera = _displayRig.FrontCamera;
        Camera floorCamera = _displayRig.FloorCamera;
        Vector3 startViewport = frontCamera.WorldToViewportPoint(start);
        Vector3 targetViewport = floorCamera.WorldToViewportPoint(target);
        float wallDisplayDistance =
            Mathf.Max(0f, startViewport.y) / Mathf.Max(0.01f, frontCamera.aspect);
        float floorDisplayDistance =
            Mathf.Max(0f, 1f - targetViewport.y) / Mathf.Max(0.01f, floorCamera.aspect);
        float totalDisplayDistance = wallDisplayDistance + floorDisplayDistance;
        float seamProgress = totalDisplayDistance > 0.0001f
            ? wallDisplayDistance / totalDisplayDistance
            : 0.5f;
        float seamViewportX = Mathf.Lerp(
            startViewport.x,
            targetViewport.x,
            seamProgress);

        Vector3 minimum = _settings.ArenaCenter - _settings.ArenaSize * 0.5f;
        Vector3 frontExit = ViewportPointOnPlane(
            frontCamera,
            new Vector2(seamViewportX, 0f),
            new Plane(Vector3.back, new Vector3(0f, 0f, start.z)),
            new Vector3(Mathf.Lerp(start.x, target.x, seamProgress), minimum.y, start.z));
        Vector3 floorEntry = ViewportPointOnPlane(
            floorCamera,
            new Vector2(seamViewportX, 1f),
            new Plane(Vector3.up, new Vector3(0f, target.y, 0f)),
            new Vector3(Mathf.Lerp(start.x, target.x, seamProgress), target.y, start.z));

        return new[] { start, frontExit, floorEntry, target };
    }

    private static Vector3 ViewportPointOnPlane(
        Camera camera,
        Vector2 viewportPoint,
        Plane plane,
        Vector3 fallback)
    {
        if (camera == null) return fallback;
        Ray ray = camera.ViewportPointToRay(
            new Vector3(viewportPoint.x, viewportPoint.y, 0f));
        return plane.Raycast(ray, out float distance)
            ? ray.GetPoint(distance)
            : fallback;
    }

    private GameObject[] CreateLaserTelegraphs(
        CaveActionPlayer attacker,
        Vector3[] path,
        bool splitByDisplay)
    {
        if (!splitByDisplay)
        {
            return new[]
            {
                CreateLaserVisual(
                    _laserTelegraphTemplate,
                    $"{attacker} Laser Telegraph",
                    path,
                    _worldEffectLayer,
                    GetPlayerColor(attacker))
            };
        }

        return new[]
        {
            CreateLaserVisual(
                _laserTelegraphTemplate,
                $"{attacker} Front Laser Telegraph",
                new[] { path[0], path[1] },
                _frontEffectLayer,
                GetPlayerColor(attacker)),
            CreateLaserVisual(
                _laserTelegraphTemplate,
                $"{attacker} Floor Laser Telegraph",
                new[] { path[2], path[3] },
                _floorEffectLayer,
                GetPlayerColor(attacker))
        };
    }

    private GameObject CreateLaserVisual(
        GameObject template,
        string objectName,
        Vector3[] path,
        int effectLayer,
        Color color)
    {
        GameObject instance = Instantiate(template, _projectilesRoot);
        instance.name = objectName;
        SetLayerRecursively(instance.transform, effectLayer);
        LineRenderer line = instance.GetComponent<LineRenderer>();
        if (line != null)
        {
            line.useWorldSpace = true;
            line.positionCount = path.Length;
            line.SetPositions(path);
        }
        ApplyEffectColor(instance, color);
        instance.SetActive(true);
        PlayEffectComponents(instance);
        _worldEffects.Add(instance);
        return instance;
    }

    private IEnumerator RunLaserAttack(
        int generation,
        CaveActionPlayer attacker,
        PlayerState defender,
        Vector2 targetPoint,
        Vector3 target,
        Vector3[] path,
        bool crossesFrontFloor,
        CaveActionSurface surface,
        Vector2 touch,
        Vector3 start,
        Vector3 inwardNormal,
        int effectLayer,
        GameObject shooter)
    {
        Vector3 approachStart = shooter != null ? shooter.transform.position : start;
        Camera surfaceCamera = GetSurfaceCamera(surface);
        Vector3 rotationUp = surfaceCamera != null ? surfaceCamera.transform.up : Vector3.up;
        Vector3 approachDirection = start - approachStart;
        Vector3 approachControl = CalculateFlightControlPoint(
            approachStart,
            start,
            rotationUp,
            _settings.LaserShooterCurveHeight);
        Vector3 aimDirection = path.Length > 1 ? path[1] - path[0] : target - start;
        Quaternion templateRotation = _laserShooterTemplate.transform.localRotation;
        Quaternion approachRotation = CreateEffectRotation(
            approachDirection,
            rotationUp,
            templateRotation);
        Quaternion arrivalRotation = CreateEffectRotation(
            start - approachControl,
            rotationUp,
            templateRotation);
        Quaternion aimRotation = CreateEffectRotation(
            aimDirection,
            rotationUp,
            templateRotation);
        if (shooter != null) shooter.transform.rotation = approachRotation;

        float approachDuration = Mathf.Max(0.05f, _settings.LaserShooterApproachDuration);
        float approachStartedAt = Time.unscaledTime;
        while (Time.unscaledTime - approachStartedAt < approachDuration)
        {
            if (generation != _attackGeneration || !_running || _gameOver)
            {
                DestroyWorldEffect(shooter);
                yield break;
            }
            if (shooter != null)
            {
                float progress = Mathf.Clamp01(
                    (Time.unscaledTime - approachStartedAt) / approachDuration);
                float eased = progress * progress * (3f - 2f * progress);
                shooter.transform.position = EvaluateQuadraticBezier(
                    approachStart,
                    approachControl,
                    start,
                    eased);
                Vector3 tangent = EvaluateQuadraticBezierTangent(
                    approachStart,
                    approachControl,
                    start,
                    eased);
                shooter.transform.rotation = CreateEffectRotation(
                    tangent,
                    rotationUp,
                    templateRotation);
            }
            yield return null;
        }
        if (shooter != null)
        {
            shooter.transform.position = start;
            shooter.transform.rotation = arrivalRotation;
        }

        float aimDuration = Mathf.Max(0.05f, _settings.LaserShooterAimDuration);
        float aimStartedAt = Time.unscaledTime;
        while (Time.unscaledTime - aimStartedAt < aimDuration)
        {
            if (generation != _attackGeneration || !_running || _gameOver)
            {
                DestroyWorldEffect(shooter);
                yield break;
            }
            if (shooter != null)
            {
                float progress = Mathf.Clamp01(
                    (Time.unscaledTime - aimStartedAt) / aimDuration);
                float eased = progress * progress * (3f - 2f * progress);
                shooter.transform.rotation = Quaternion.Slerp(
                    arrivalRotation,
                    aimRotation,
                    eased);
            }
            yield return null;
        }
        if (shooter != null) shooter.transform.rotation = aimRotation;

        GameObject spawnerTemplate = surface == CaveActionSurface.FrontWall
            ? _frontSpawnerTemplate
            : _wallSpawnerTemplate;
        GameObject spawner = SpawnWorldEffect(
            spawnerTemplate,
            start,
            inwardNormal,
            lifetime: 0f,
            effectLayer: effectLayer);
        ApplyEffectColor(spawner, GetPlayerColor(attacker));
        GameObject[] telegraphs = CreateLaserTelegraphs(
            attacker,
            path,
            crossesFrontFloor);

        float warningEndsAt = Time.unscaledTime + Mathf.Max(0.05f, _settings.LaserTelegraphDuration);
        while (Time.unscaledTime < warningEndsAt)
        {
            if (generation != _attackGeneration || !_running || _gameOver)
            {
                DestroyWorldEffects(telegraphs);
                DestroyWorldEffect(spawner);
                DestroyWorldEffect(shooter);
                yield break;
            }
            bool lineVisible = Mathf.PingPong(Time.unscaledTime * 7f, 1f) > 0.25f;
            foreach (GameObject telegraph in telegraphs)
            {
                if (telegraph == null) continue;
                LineRenderer warningLine = telegraph.GetComponent<LineRenderer>();
                if (warningLine != null) warningLine.enabled = lineVisible;
            }
            yield return null;
        }

        DestroyWorldEffects(telegraphs);
        SoundManager.Instance.PlaySound(SoundType.Shoot_laser_strong);
        _asteroidController?.HitByLaser(path, crossesFrontFloor);
        GameObject beam = CreateLaserBeam(attacker, path, crossesFrontFloor);

        float beamDuration = Mathf.Max(0.05f, _settings.LaserBeamDuration);
        float beamStartedAt = Time.unscaledTime;
        while (Time.unscaledTime - beamStartedAt < beamDuration)
        {
            if (generation != _attackGeneration || !_running || _gameOver)
            {
                DestroyWorldEffect(beam);
                DestroyWorldEffect(spawner);
                DestroyWorldEffect(shooter);
                yield break;
            }
            if (beam != null)
            {
                float progress = Mathf.Clamp01((Time.unscaledTime - beamStartedAt) / beamDuration);
                ApplyLaserPathPosition(beam.transform, path, progress, crossesFrontFloor);
            }
            yield return null;
        }

        if (beam != null) ApplyLaserPathPosition(beam.transform, path, 1f, crossesFrontFloor);
        GameObject impact = SpawnWorldEffect(
            _impactEffectTemplate,
            target,
            Vector3.up,
            _settings.ImpactEffectLifetime,
            crossesFrontFloor ? _floorEffectLayer : _worldEffectLayer);
        ApplyEffectColor(impact, GetPlayerColor(attacker));

        if (defender.HasPlatform)
        {
            Rect hitRect = defender.PlatformRect;
            float radius = Mathf.Max(0f, _settings.LaserHitRadius);
            hitRect.xMin -= radius;
            hitRect.xMax += radius;
            hitRect.yMin -= radius;
            hitRect.yMax += radius;
            if (hitRect.Contains(targetPoint)) ApplyDamage(defender);
        }

        DestroyWorldEffect(beam);
        DestroyWorldEffect(spawner);

        if (generation != _attackGeneration || !_running || _gameOver)
        {
            DestroyWorldEffect(shooter);
            yield break;
        }

        float margin = Mathf.Max(0.01f, _settings.LaserShooterOffscreenMargin);
        Vector2 exitTouch = touch;
        exitTouch.x = touch.x < 0.5f ? 1f + margin : -margin;
        Vector3 exitPosition = SurfaceToWorld(surface, exitTouch) +
                               inwardNormal * Mathf.Max(0f, _settings.WorldEffectSurfaceOffset);
        Vector3 exitControl = CalculateFlightControlPoint(
            start,
            exitPosition,
            rotationUp,
            _settings.LaserShooterCurveHeight);
        Quaternion exitStartRotation = shooter != null
            ? shooter.transform.rotation
            : aimRotation;
        float exitDuration = Mathf.Max(0.05f, _settings.LaserShooterExitDuration);
        float exitStartedAt = Time.unscaledTime;
        while (Time.unscaledTime - exitStartedAt < exitDuration)
        {
            if (generation != _attackGeneration || !_running || _gameOver)
            {
                DestroyWorldEffect(shooter);
                yield break;
            }
            if (shooter != null)
            {
                float progress = Mathf.Clamp01(
                    (Time.unscaledTime - exitStartedAt) / exitDuration);
                float eased = progress * progress * (3f - 2f * progress);
                shooter.transform.position = EvaluateQuadraticBezier(
                    start,
                    exitControl,
                    exitPosition,
                    eased);
                Vector3 tangent = EvaluateQuadraticBezierTangent(
                    start,
                    exitControl,
                    exitPosition,
                    eased);
                Quaternion flightRotation = CreateEffectRotation(
                    tangent,
                    rotationUp,
                    templateRotation);
                float turnProgress = Mathf.SmoothStep(
                    0f,
                    1f,
                    Mathf.Clamp01(progress / 0.3f));
                shooter.transform.rotation = Quaternion.Slerp(
                    exitStartRotation,
                    flightRotation,
                    turnProgress);
            }
            yield return null;
        }
        DestroyWorldEffect(shooter);
    }

    private GameObject CreateLaserBeam(
        CaveActionPlayer attacker,
        Vector3[] path,
        bool crossesFrontFloor)
    {
        GameObject template = attacker == CaveActionPlayer.Left
            ? _redLaserBeamTemplate
            : _blueLaserBeamTemplate;
        GameObject instance = Instantiate(template, _projectilesRoot);
        instance.name = $"{attacker} Laser Beam";
        SetLayerRecursively(
            instance.transform,
            crossesFrontFloor ? _frontEffectLayer : _worldEffectLayer);
        ApplyLaserPathPosition(instance.transform, path, 0f, crossesFrontFloor);
        foreach (Collider collider in instance.GetComponentsInChildren<Collider>(true))
        {
            collider.enabled = false;
        }
        ApplyEffectColor(instance, GetPlayerColor(attacker));
        instance.SetActive(true);
        PlayEffectComponents(instance);
        _worldEffects.Add(instance);
        return instance;
    }

    private void ApplyLaserPathPosition(
        Transform beam,
        IReadOnlyList<Vector3> path,
        float progress,
        bool crossesFrontFloor)
    {
        if (crossesFrontFloor && path.Count >= 4)
        {
            float frontLength = Vector3.Distance(path[0], path[1]);
            float floorLength = Vector3.Distance(path[2], path[3]);
            float totalVisibleLength = frontLength + floorLength;
            float traveled = Mathf.Clamp01(progress) * totalVisibleLength;
            bool onFront = traveled <= frontLength;
            Vector3 from = onFront ? path[0] : path[2];
            Vector3 to = onFront ? path[1] : path[3];
            float segmentLength = onFront ? frontLength : floorLength;
            float segmentDistance = onFront ? traveled : traveled - frontLength;
            float segmentProgress = segmentLength > 0.0001f
                ? Mathf.Clamp01(segmentDistance / segmentLength)
                : 1f;

            int segmentLayer = onFront ? _frontEffectLayer : _floorEffectLayer;
            if (beam.gameObject.layer != segmentLayer)
            {
                SetLayerRecursively(beam, segmentLayer);
            }
            beam.position = Vector3.Lerp(from, to, segmentProgress);
            Vector3 direction = to - from;
            if (direction.sqrMagnitude > 0.0001f)
            {
                beam.rotation = Quaternion.LookRotation(direction.normalized, Vector3.up);
            }
            return;
        }

        float totalLength = 0f;
        for (int i = 1; i < path.Count; i++)
        {
            totalLength += Vector3.Distance(path[i - 1], path[i]);
        }

        float remaining = Mathf.Clamp01(progress) * totalLength;
        for (int i = 1; i < path.Count; i++)
        {
            Vector3 from = path[i - 1];
            Vector3 to = path[i];
            float segmentLength = Vector3.Distance(from, to);
            if (remaining <= segmentLength || i == path.Count - 1)
            {
                float segmentProgress = segmentLength > 0.0001f
                    ? Mathf.Clamp01(remaining / segmentLength)
                    : 1f;
                beam.position = Vector3.Lerp(from, to, segmentProgress);
                Vector3 direction = to - from;
                if (direction.sqrMagnitude > 0.0001f)
                {
                    beam.rotation = Quaternion.LookRotation(direction.normalized, Vector3.up);
                }
                return;
            }
            remaining -= segmentLength;
        }
    }

    private Vector3 SurfaceToWorld(
        CaveActionSurface surface,
        Vector2 point)
    {
        Vector3 minimum = _settings.ArenaCenter - _settings.ArenaSize * 0.5f;
        float floorY = minimum.y;
        float y = Mathf.Lerp(floorY, floorY + _settings.ArenaSize.y, point.y);
        if (surface == CaveActionSurface.FrontWall)
        {
            Camera frontCamera = _displayRig.FrontCamera;
            if (frontCamera != null)
            {
                Ray ray = frontCamera.ViewportPointToRay(new Vector3(point.x, point.y, 0f));
                float frontZ = minimum.z + _settings.ArenaSize.z;
                Plane frontPlane = new(Vector3.back, new Vector3(0f, 0f, frontZ));
                if (frontPlane.Raycast(ray, out float distance))
                {
                    return ray.GetPoint(distance);
                }
            }

            return new Vector3(
                Mathf.Lerp(minimum.x, minimum.x + _settings.ArenaSize.x, point.x),
                y,
                minimum.z + _settings.ArenaSize.z);
        }

        Camera wallCamera = surface == CaveActionSurface.LeftWall
            ? _displayRig.LeftCamera
            : _displayRig.RightCamera;
        if (wallCamera != null)
        {
            Ray ray = wallCamera.ViewportPointToRay(new Vector3(point.x, point.y, 0f));
            Plane arenaPlane = new(Vector3.up, new Vector3(0f, minimum.y, 0f));
            if (arenaPlane.Raycast(ray, out float distance))
            {
                return ray.GetPoint(distance);
            }
        }

        // 카메라를 찾지 못한 경우에도 각 측벽 카메라의 수평 방향을 맞춘다.
        float wallX = surface == CaveActionSurface.LeftWall
            ? minimum.x
            : minimum.x + _settings.ArenaSize.x;
        float wallDepth = surface == CaveActionSurface.LeftWall ? point.x : 1f - point.x;
        return new Vector3(
            wallX,
            y,
            Mathf.Lerp(minimum.z, minimum.z + _settings.ArenaSize.z, wallDepth));
    }

    private static Vector3 GetSurfaceInwardNormal(CaveActionSurface surface)
    {
        if (surface == CaveActionSurface.FrontWall)
        {
            return Vector3.back;
        }
        return surface == CaveActionSurface.LeftWall ? Vector3.right : Vector3.left;
    }

    private Camera GetSurfaceCamera(CaveActionSurface surface)
    {
        return surface switch
        {
            CaveActionSurface.LeftWall => _displayRig.LeftCamera,
            CaveActionSurface.RightWall => _displayRig.RightCamera,
            _ => _displayRig.FrontCamera
        };
    }

    private static Quaternion CreateEffectRotation(
        Vector3 direction,
        Vector3 up,
        Quaternion templateRotation)
    {
        if (direction.sqrMagnitude <= 0.0001f) return templateRotation;

        Vector3 forward = direction.normalized;
        Vector3 normalizedUp = up.sqrMagnitude > 0.0001f ? up.normalized : Vector3.up;
        if (Mathf.Abs(Vector3.Dot(forward, normalizedUp)) > 0.98f)
        {
            normalizedUp = Mathf.Abs(Vector3.Dot(forward, Vector3.up)) < 0.98f
                ? Vector3.up
                : Vector3.right;
        }
        return Quaternion.LookRotation(forward, normalizedUp) * templateRotation;
    }

    private static Vector3 CalculateFlightControlPoint(
        Vector3 from,
        Vector3 to,
        Vector3 curveDirection,
        float curveHeight)
    {
        Vector3 direction = curveDirection.sqrMagnitude > 0.0001f
            ? curveDirection.normalized
            : Vector3.up;
        float distance = Vector3.Distance(from, to);
        return (from + to) * 0.5f +
               direction * distance * Mathf.Clamp01(curveHeight);
    }

    private static Vector3 EvaluateQuadraticBezier(
        Vector3 from,
        Vector3 control,
        Vector3 to,
        float progress)
    {
        float t = Mathf.Clamp01(progress);
        float inverse = 1f - t;
        return inverse * inverse * from +
               2f * inverse * t * control +
               t * t * to;
    }

    private static Vector3 EvaluateQuadraticBezierTangent(
        Vector3 from,
        Vector3 control,
        Vector3 to,
        float progress)
    {
        float t = Mathf.Clamp01(progress);
        return 2f * (1f - t) * (control - from) +
               2f * t * (to - control);
    }

    private GameObject SpawnWorldEffect(
        GameObject template,
        Vector3 position,
        Vector3 surfaceNormal,
        float lifetime,
        int effectLayer = -1)
    {
        if (template == null || _worldEffectsRoot == null)
        {
            return null;
        }

        GameObject instance = Instantiate(template, _worldEffectsRoot);
        instance.name = $"{template.name} Instance";
        SetLayerRecursively(
            instance.transform,
            effectLayer >= 0 ? effectLayer : _worldEffectLayer);
        instance.transform.position = position;
        Quaternion basis = Mathf.Abs(Vector3.Dot(surfaceNormal.normalized, Vector3.up)) > 0.99f
            ? Quaternion.LookRotation(Vector3.forward, surfaceNormal.normalized)
            : Quaternion.LookRotation(surfaceNormal.normalized, Vector3.up);
        instance.transform.rotation = basis * template.transform.localRotation;
        instance.SetActive(true);
        PlayEffectComponents(instance);
        _worldEffects.Add(instance);

        if (lifetime > 0f)
        {
            CaveActionEffectLifetime effectLifetime = instance.AddComponent<CaveActionEffectLifetime>();
            effectLifetime.Begin(lifetime, () => _worldEffects.Remove(instance));
        }
        return instance;
    }

    private static void ApplyEffectColor(GameObject instance, Color color)
    {
        if (instance == null) return;

        foreach (LineRenderer line in instance.GetComponentsInChildren<LineRenderer>(true))
        {
            line.startColor = color;
            line.endColor = color;
        }
        foreach (TrailRenderer trail in instance.GetComponentsInChildren<TrailRenderer>(true))
        {
            trail.startColor = color;
            trail.endColor = new Color(color.r, color.g, color.b, 0f);
        }
        foreach (ParticleSystem particles in instance.GetComponentsInChildren<ParticleSystem>(true))
        {
            ParticleSystem.MainModule main = particles.main;
            main.startColor = color;
        }
        foreach (Light effectLight in instance.GetComponentsInChildren<Light>(true))
        {
            effectLight.color = color;
        }

        MaterialPropertyBlock block = new();
        foreach (Renderer renderer in instance.GetComponentsInChildren<Renderer>(true))
        {
            Material[] materials = renderer.sharedMaterials;
            for (int materialIndex = 0; materialIndex < materials.Length; materialIndex++)
            {
                Material material = materials[materialIndex];
                if (material == null) continue;

                block.Clear();
                renderer.GetPropertyBlock(block, materialIndex);
                if (material.HasProperty(BaseColorId)) block.SetColor(BaseColorId, color);
                if (material.HasProperty(ColorId)) block.SetColor(ColorId, color);
                if (material.HasProperty(TintColorId)) block.SetColor(TintColorId, color);
                renderer.SetPropertyBlock(block, materialIndex);
            }
        }
    }

    private static void PlayEffectComponents(GameObject instance)
    {
        foreach (ParticleSystem particles in instance.GetComponentsInChildren<ParticleSystem>(true))
        {
            particles.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            particles.Play(true);
        }
        foreach (AudioSource audioSource in instance.GetComponentsInChildren<AudioSource>(true))
        {
            if (audioSource.enabled) audioSource.Play();
        }
    }

    private void DestroyWorldEffect(GameObject effect)
    {
        if (effect == null) return;
        _worldEffects.Remove(effect);
        Destroy(effect);
    }

    private void DestroyWorldEffects(IEnumerable<GameObject> effects)
    {
        if (effects == null) return;
        foreach (GameObject effect in effects)
        {
            DestroyWorldEffect(effect);
        }
    }

    private void ConfigureEffectCameraLayers()
    {
        int frontMask = 1 << _frontEffectLayer;
        int floorMask = 1 << _floorEffectLayer;

        if (_displayRig.FrontCamera != null)
        {
            _displayRig.FrontCamera.cullingMask =
                (_displayRig.FrontCamera.cullingMask | frontMask) & ~floorMask;
        }
        if (_displayRig.FloorCamera != null)
        {
            _displayRig.FloorCamera.cullingMask =
                (_displayRig.FloorCamera.cullingMask | floorMask) & ~frontMask;
        }
        if (_displayRig.LeftCamera != null)
        {
            _displayRig.LeftCamera.cullingMask &= ~(frontMask | floorMask);
        }
        if (_displayRig.RightCamera != null)
        {
            _displayRig.RightCamera.cullingMask &= ~(frontMask | floorMask);
        }
    }

    private Vector3 FloorToWorld(Vector2 point)
    {
        Vector3 minimum = _settings.ArenaCenter - _settings.ArenaSize * 0.5f;
        return new Vector3(
            Mathf.Lerp(minimum.x, minimum.x + _settings.ArenaSize.x, point.x),
            minimum.y,
            Mathf.Lerp(minimum.z, minimum.z + _settings.ArenaSize.z, point.y));
    }

    private void SpawnHazard(PlayerState attacker)
    {
        CaveActionPlayer defenderSide = Opposite(attacker.Side);
        Vector2 sourceSize = attacker.HasPlatform
            ? attacker.PlatformRect.size
            : _settings.PlatformFixedSize;
        Vector2 sourceCenter = attacker.HasPlatform
            ? attacker.PlatformRect.center
            : new Vector2(attacker.Side == CaveActionPlayer.Left ? 0.25f : 0.75f, 0.5f);
        Vector2 size = sourceSize * Mathf.Clamp01(_settings.HazardSizeMultiplier);
        for (int i = _hazards.Count - 1; i >= 0; i--)
        {
            if (_hazards[i].Attacker != attacker.Side) continue;
            if (_hazards[i].Image != null) Destroy(_hazards[i].Image.gameObject);
            _hazards.RemoveAt(i);
        }

        Rect hazardRect = CaveActionRules.MirrorHorizontally(
            new Rect(sourceCenter - size * 0.5f, size));

        Image image = Instantiate(_hazardTemplate, _hazardsRoot);
        image.name = $"{defenderSide} Floor Hazard";
        image.color = GetPlayerColor(attacker.Side);
        image.gameObject.SetActive(true);
        image.raycastTarget = false;
        RectTransform rect = image.rectTransform;
        ApplyNormalizedRect(rect, hazardRect);
        _hazards.Add(new HazardState
        {
            Image = image,
            Rect = hazardRect,
            Size = size,
            Attacker = attacker.Side,
            Defender = defenderSide
        });
    }

    private void UpdateHazards()
    {
        for (int i = _hazards.Count - 1; i >= 0; i--)
        {
            HazardState hazard = _hazards[i];
            if (hazard.Image == null)
            {
                _hazards.RemoveAt(i);
                continue;
            }
            PlayerState attacker = GetPlayer(hazard.Attacker);
            if (!attacker.HasPlatform)
            {
                hazard.Image.gameObject.SetActive(true);
                continue;
            }

            hazard.Image.gameObject.SetActive(true);
            hazard.Rect = CaveActionRules.MirrorHorizontally(
                new Rect(
                    attacker.PlatformRect.center - hazard.Size * 0.5f,
                    hazard.Size));
            ApplyNormalizedRect(hazard.Image.rectTransform, hazard.Rect);

            PlayerState defender = GetPlayer(hazard.Defender);
            if (defender.HasPlatform && hazard.Rect.Overlaps(defender.PlatformRect))
            {
                ApplyDamage(defender);
                if (_gameOver) return;
            }
        }
    }

    private void UpdateAsteroidContacts()
    {
        if (_asteroidController == null) return;

        _asteroidContactRects.Clear();
        if (_leftPlayer.HasPlatform) _asteroidContactRects.Add(_leftPlayer.PlatformRect);
        if (_rightPlayer.HasPlatform) _asteroidContactRects.Add(_rightPlayer.PlatformRect);
        foreach (HazardState hazard in _hazards)
        {
            if (hazard?.Image != null && hazard.Image.gameObject.activeInHierarchy)
            {
                _asteroidContactRects.Add(hazard.Rect);
            }
        }
        _asteroidController.CheckContacts(_asteroidContactRects);
    }

    private void SpawnScanLine(CaveActionPlayer defender)
    {
        Image image = Instantiate(_scanLineTemplate, _scanLinesRoot);
        image.name = $"{defender} Scan Line";
        image.color = GetPlayerColor(_attacker);
        image.raycastTarget = false;
        image.gameObject.SetActive(true);
        _scanLines.Add(new ScanLineState
        {
            Image = image,
            Defender = defender,
            StartedAt = Time.unscaledTime
        });
    }

    private void UpdateScanLines()
    {
        float duration = Mathf.Max(0.1f, _settings.ScanLineDuration);
        Rect canvasRect = _floorCanvas.rect;
        for (int i = _scanLines.Count - 1; i >= 0; i--)
        {
            ScanLineState line = _scanLines[i];
            PlayerState defender = GetPlayer(line.Defender);
            if (!defender.HasPlatform && defender.EverDetected)
            {
                line.DefenderJumped = true;
            }
            float progress = (Time.unscaledTime - line.StartedAt) / duration;
            if (progress >= 1f)
            {
                if (line.Image != null) Destroy(line.Image.gameObject);
                _scanLines.RemoveAt(i);
                if (line.DefenderJumped)
                {
                    ShowAnnouncement(
                        "DODGE!",
                        GetPlayerColor(line.Defender),
                        0.8f,
                        SoundType.StartWave_Electro01);
                }
                continue;
            }

            float normalizedY = 1f - Mathf.Clamp01(progress);
            RectTransform rect = line.Image.rectTransform;
            rect.anchorMin = rect.anchorMax = new Vector2(0.5f, 0.5f);
            rect.sizeDelta = new Vector2(canvasRect.width * 0.5f, _settings.ScanLineWidth);
            float centerX = line.Defender == CaveActionPlayer.Left ? -canvasRect.width * 0.25f : canvasRect.width * 0.25f;
            rect.anchoredPosition = new Vector2(
                centerX,
                (normalizedY - 0.5f) * canvasRect.height);

            if (defender.HasPlatform &&
                Time.unscaledTime >= defender.JumpInvulnerableUntil &&
                normalizedY >= defender.PlatformRect.yMin &&
                normalizedY <= defender.PlatformRect.yMax)
            {
                bool damaged = ApplyDamage(defender);
                if (_gameOver) return;
                if (damaged)
                {
                    Destroy(line.Image.gameObject);
                    _scanLines.RemoveAt(i);
                }
            }
        }
    }

    private bool ApplyDamage(PlayerState defender)
    {
        if (_gameOver || Time.unscaledTime < defender.InvulnerableUntil) return false;

        defender.Health = Mathf.Max(0, defender.Health - 1);
        defender.InvulnerableUntil = Time.unscaledTime + Mathf.Max(0f, _settings.InvulnerabilityDuration);
        PlayHitFeedback(defender.Side);
        RefreshRoleGuide();
        StartCoroutine(FlashPlatform(defender));
        if (defender.Health <= 0)
        {
            BeginGameOver(defender);
        }
        return true;
    }

    private void PlayHitFeedback(CaveActionPlayer defender)
    {
        SoundManager.Instance.PlaySound(SoundType.Explosion_ArcaneEnergyPlasma03v2);
        float duration = Mathf.Max(0.01f, _settings.HitShakeDuration);
        float position = Mathf.Max(0f, _settings.HitShakePosition);
        float rotation = Mathf.Max(0f, _settings.HitShakeRotation);
        CaveBallCameraShake sideShake = defender == CaveActionPlayer.Left
            ? _leftCameraShake
            : _rightCameraShake;
        sideShake?.Shake(duration, position, rotation);
        _frontCameraShake?.Shake(duration, position * 0.65f, rotation * 0.65f);
        _floorCameraShake?.Shake(duration, position * 0.5f, rotation * 0.5f);
    }

    private IEnumerator FlashPlatform(PlayerState player)
    {
        if (player.PlatformImage == null) yield break;
        Color original = player.PlatformImage.color;
        float end = Time.unscaledTime + Mathf.Min(0.45f, _settings.InvulnerabilityDuration);
        while (Time.unscaledTime < end && player.PlatformImage != null)
        {
            player.PlatformImage.color = Color.Lerp(original, Color.white, Mathf.PingPong(Time.unscaledTime * 10f, 1f));
            yield return null;
        }
        if (player.PlatformImage != null) SetPlatformColor(player);
    }

    private void BeginGameOver(PlayerState loser)
    {
        _gameOver = true;
        if (_turnAnnouncementCoroutine != null)
        {
            StopCoroutine(_turnAnnouncementCoroutine);
            _turnAnnouncementCoroutine = null;
        }
        if (_turnAnnouncementRoot != null) _turnAnnouncementRoot.gameObject.SetActive(false);
        if (_roleGuideRoot != null) _roleGuideRoot.gameObject.SetActive(false);
        SetPlatformVisible(loser, false);
        ClearAttacks();
        _asteroidController?.PauseSession();
        _silhouette?.PlayGameOver(loser.Side);
        _restartCoroutine = StartCoroutine(RestartAfterDelay());
    }

    private IEnumerator RestartAfterDelay()
    {
        yield return new WaitForSecondsRealtime(Mathf.Max(0.1f, _settings.GameRestartDelay));
        _restartCoroutine = null;
        if (isActiveAndEnabled) ResetGame();
    }

    private void SwitchRoles()
    {
        ClearAttacks();
        _attacker = Opposite(_attacker);
        SelectAttackMode();
        _roundEndsAt = Time.unscaledTime + Mathf.Max(1f, _settings.AttackDuration);
        UpdatePlatformColors();
        RefreshRoleGuide();
        AnnounceTurn();
#if UNITY_EDITOR
        if (_settings.EnableEditorMouseInput)
        {
            Debug.Log($"[CaveAction Editor Test] {_attacker} 플레이어로 공수 전환");
        }
#endif
    }

    private void ClearAttacks()
    {
        _attackGeneration++;
        foreach (GameObject effect in _worldEffects)
        {
            if (effect != null) Destroy(effect);
        }
        _worldEffects.Clear();
        foreach (HazardState hazard in _hazards)
        {
            if (hazard.Image != null) Destroy(hazard.Image.gameObject);
        }
        _hazards.Clear();
        foreach (ScanLineState line in _scanLines)
        {
            if (line.Image != null) Destroy(line.Image.gameObject);
        }
        _scanLines.Clear();
        _leftWallTouches.Clear();
        _rightWallTouches.Clear();
        _frontWallTouches.Clear();
    }

    private void UpdatePlatformColors()
    {
        SetPlatformColor(_leftPlayer);
        SetPlatformColor(_rightPlayer);
    }

    private void SetPlatformColor(PlayerState player)
    {
        if (player?.PlatformImage == null) return;
        Color color = GetPlayerColor(player.Side);
        color.a = player.Side == _attacker ? 1f : 0.72f;
        player.PlatformImage.color = color;
    }

    private void SetPlatformVisible(PlayerState player, bool visible)
    {
        if (player?.PlatformImage != null)
        {
            player.PlatformImage.gameObject.SetActive(visible);
        }
    }

    private void ApplyNormalizedRect(RectTransform target, Rect normalized)
    {
        Rect canvasRect = _floorCanvas.rect;
        target.anchorMin = target.anchorMax = new Vector2(0.5f, 0.5f);
        target.sizeDelta = new Vector2(normalized.width * canvasRect.width, normalized.height * canvasRect.height);
        target.anchoredPosition = new Vector2(
            (normalized.center.x - 0.5f) * canvasRect.width,
            (normalized.center.y - 0.5f) * canvasRect.height);
    }

    private PlayerState GetPlayer(CaveActionPlayer side)
    {
        return side == CaveActionPlayer.Left ? _leftPlayer : _rightPlayer;
    }

    private Color GetPlayerColor(CaveActionPlayer side)
    {
        return side == CaveActionPlayer.Left ? _settings.LeftPlayerColor : _settings.RightPlayerColor;
    }

    private static CaveActionPlayer Opposite(CaveActionPlayer side)
    {
        return side == CaveActionPlayer.Left ? CaveActionPlayer.Right : CaveActionPlayer.Left;
    }

    private static Vector2 Normalize(Vector2 raw, CaveActionSensorCalibration calibration)
    {
        return CaveActionRules.NormalizePoint(
            raw,
            calibration.Minimum,
            calibration.Maximum,
            calibration.InvertX,
            calibration.InvertY);
    }

    private Transform FindDeepTransform(string objectName)
    {
        foreach (Transform child in GetComponentsInChildren<Transform>(true))
        {
            if (child.name == objectName) return child;
        }
        return null;
    }

    private GameObject[] FindTemplates(params string[] names)
    {
        GameObject[] templates = new GameObject[names.Length];
        for (int i = 0; i < names.Length; i++)
        {
            templates[i] = FindDeepTransform(names[i])?.gameObject;
        }
        return templates;
    }

    private static bool ContainsNull(IReadOnlyList<GameObject> objects)
    {
        if (objects == null || objects.Count == 0) return true;
        for (int i = 0; i < objects.Count; i++)
        {
            if (objects[i] == null) return true;
        }
        return false;
    }

    private static void SetLayerRecursively(Transform root, int layer)
    {
        foreach (Transform child in root.GetComponentsInChildren<Transform>(true))
        {
            child.gameObject.layer = layer;
        }
    }

    private static CaveBallCameraShake GetOrAddCameraShake(Camera cameraComponent)
    {
        if (cameraComponent == null) return null;
        CaveBallCameraShake shake = cameraComponent.GetComponent<CaveBallCameraShake>();
        return shake != null
            ? shake
            : cameraComponent.gameObject.AddComponent<CaveBallCameraShake>();
    }

    private T FindDeepComponent<T>(string objectName, Transform under = null) where T : Component
    {
        Transform root = under != null ? under : transform;
        foreach (T component in root.GetComponentsInChildren<T>(true))
        {
            if (component.name == objectName) return component;
        }
        return null;
    }

    private void OnDestroy()
    {
        StopGame();
    }
}

public enum CaveActionSurface
{
    LeftWall,
    RightWall,
    FrontWall
}

public sealed class CaveActionEffectLifetime : MonoBehaviour
{
    private float _destroyAt;
    private Action _onExpired;

    public void Begin(float lifetime, Action onExpired)
    {
        _destroyAt = Time.unscaledTime + Mathf.Max(0.05f, lifetime);
        _onExpired = onExpired;
    }

    private void Update()
    {
        if (Time.unscaledTime < _destroyAt) return;
        Action callback = _onExpired;
        _onExpired = null;
        callback?.Invoke();
        Destroy(gameObject);
    }
}
