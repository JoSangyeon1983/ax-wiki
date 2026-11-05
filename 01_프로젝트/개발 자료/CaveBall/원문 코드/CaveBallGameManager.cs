using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using CellBig;
public sealed class CaveBallGameManager : MonoBehaviour
{
    private readonly List<CaveBallBrick> _bricks = new();

    private CaveBallSetting _settings;
    private CaveBallDisplayRig _displayRig;
    private CaveBall _ball;
    private CaveBallMLInteraction _mlInteraction;
    private CaveBallFloorInteraction _floorInteraction;
    private CaveBallEffectPool _redBreakPool;
    private CaveBallEffectPool _blueBreakPool;
    private CaveBallCameraShake _leftCameraShake;
    private CaveBallCameraShake _rightCameraShake;
    private CaveBallScoreboard _scoreboard;
    private Coroutine _roundResetCoroutine;
    private int _remainingBricks;
    private int _redScore;
    private int _blueScore;
    private bool _running;

    public CaveBall Ball => _ball;
    public int RemainingBricks => _remainingBricks;
    public int RedScore => _redScore;
    public int BlueScore => _blueScore;

    public bool Initialize(CaveBallSetting settings, CaveBallDisplayRig displayRig)
    {
        _settings = settings;
        _displayRig = displayRig;
        _ball = GetComponentInChildren<CaveBall>(true);
        if (_ball == null)
        {
            Debug.LogError("[CaveBallGameManager] CaveballBG에서 Ball을 찾지 못했습니다.");
            return false;
        }

        ConfigureBricks();
        ConfigureEffectPools();
        _leftCameraShake = GetOrAddCameraShake(displayRig.LeftCamera);
        _rightCameraShake = GetOrAddCameraShake(displayRig.RightCamera);
        _scoreboard = GetComponent<CaveBallScoreboard>();
        if (_scoreboard == null)
        {
            _scoreboard = gameObject.AddComponent<CaveBallScoreboard>();
        }
        _scoreboard.Initialize(settings, displayRig.FrontCamera);
        _ball.Configure(settings, this);

        _mlInteraction = gameObject.AddComponent<CaveBallMLInteraction>();
        _mlInteraction.Initialize(_ball, settings, displayRig.FrontCamera);

        _floorInteraction = gameObject.AddComponent<CaveBallFloorInteraction>();
        _floorInteraction.Initialize(_ball, settings, displayRig.FloorCamera);

        return true;
    }

    public void StartGame()
    {
        if (_running || _ball == null)
        {
            return;
        }

        SoundManager.Instance.PlaySound(SoundType.ArcadeGameBGM3_Loop);

        _running = true;
        ResetRound();
        _mlInteraction.StartSession();
        _floorInteraction.StartListening();
    }

    public void StopGame()
    {
        _running = false;
        if (_roundResetCoroutine != null)
        {
            StopCoroutine(_roundResetCoroutine);
            _roundResetCoroutine = null;
        }

        _mlInteraction?.StopSession();
        _floorInteraction?.StopListening();
        _redBreakPool?.StopAll();
        _blueBreakPool?.StopAll();
        _ball?.StopMotion();
    }

    public void NotifyBrickDestroyed(CaveBallBrick brick)
    {
        if (!_running || brick == null)
        {
            return;
        }

        CaveBallEffectPool effectPool = brick.BrickColor == CaveBallBrickColor.Red
            ? _redBreakPool
            : _blueBreakPool;
        effectPool?.Play(brick.transform.position);
        CaveBallCameraShake cameraShake = brick.BrickColor == CaveBallBrickColor.Red
            ? _leftCameraShake
            : _rightCameraShake;
        cameraShake?.Shake(
            _settings.BrickCameraShakeDuration,
            _settings.BrickCameraShakePosition,
            _settings.BrickCameraShakeRotation);

        SoundManager.Instance.PlaySound(SoundType.Explosion_ArcaneEnergyPlasma03v2);

        CaveBallBrickColor scoringColor;
        if (brick.BrickColor == CaveBallBrickColor.Red)
        {
            _blueScore++;
            scoringColor = CaveBallBrickColor.Blue;
        }
        else
        {
            _redScore++;
            scoringColor = CaveBallBrickColor.Red;
        }
        _scoreboard?.Increment(
            scoringColor,
            _redScore,
            _blueScore);

        _remainingBricks = Mathf.Max(0, _remainingBricks - 1);
        if (_remainingBricks == 0 && _roundResetCoroutine == null)
        {
            _roundResetCoroutine = StartCoroutine(ResetRoundAfterDelay());
        }
    }

    private void ConfigureBricks()
    {
        _bricks.Clear();
        Transform leftRoot = FindDeepChild(transform, "LeftBricks");
        Transform rightRoot = FindDeepChild(transform, "RightBricks");

        foreach (CaveBallBrick brick in GetComponentsInChildren<CaveBallBrick>(true))
        {
            CaveBallBrickColor color = rightRoot != null && brick.transform.IsChildOf(rightRoot)
                ? CaveBallBrickColor.Blue
                : CaveBallBrickColor.Red;

            if (leftRoot == null && rightRoot == null)
            {
                Debug.LogWarning("[CaveBallGameManager] 벽돌 그룹을 찾지 못해 기본 Red로 설정합니다.");
            }

            brick.Configure(color);
            SetLayerRecursively(brick.gameObject, color == CaveBallBrickColor.Red ? "LeftArea" : "RightArea");
            _bricks.Add(brick);
        }
    }

    private void ConfigureEffectPools()
    {
        _redBreakPool = CreateEffectPool(
            "Red Brick Break Pool",
            "BrickBreakRed",
            "LeftArea");
        _blueBreakPool = CreateEffectPool(
            "Blue Brick Break Pool",
            "BrickBreakBlue",
            "RightArea");
    }

    private CaveBallEffectPool CreateEffectPool(
        string poolName,
        string templateName,
        string layerName)
    {
        Transform template = FindDeepChild(transform, templateName);
        if (template == null)
        {
            Debug.LogError($"[CaveBallGameManager] '{templateName}' 효과를 찾지 못했습니다.");
            return null;
        }

        GameObject poolObject = new GameObject(poolName);
        poolObject.transform.SetParent(transform, false);
        CaveBallEffectPool pool = poolObject.AddComponent<CaveBallEffectPool>();
        pool.Initialize(
            template.gameObject,
            _settings.BrickBreakPoolSize,
            _settings.BrickBreakEffectDuration,
            layerName);
        return pool;
    }

    private static CaveBallCameraShake GetOrAddCameraShake(Camera cameraComponent)
    {
        if (cameraComponent == null)
        {
            return null;
        }

        CaveBallCameraShake shake = cameraComponent.GetComponent<CaveBallCameraShake>();
        return shake != null ? shake : cameraComponent.gameObject.AddComponent<CaveBallCameraShake>();
    }

    private IEnumerator ResetRoundAfterDelay()
    {
        _ball.StopMotion();
        yield return new WaitForSecondsRealtime(_settings.RoundResetDelay);

        if (_running)
        {
            ResetRound();
        }

        _roundResetCoroutine = null;
    }

    private void ResetRound()
    {
        foreach (CaveBallBrick brick in _bricks)
        {
            brick.ResetBrick();
        }

        _remainingBricks = _bricks.Count;
        _redScore = 0;
        _blueScore = 0;
        _scoreboard?.SetScores(_redScore, _blueScore);
        _ball.ResetForRound();
    }

    private static Transform FindDeepChild(Transform root, string objectName)
    {
        foreach (Transform child in root.GetComponentsInChildren<Transform>(true))
        {
            if (child.name == objectName)
            {
                return child;
            }
        }

        return null;
    }

    private static void SetLayerRecursively(GameObject root, string layerName)
    {
        int layer = LayerMask.NameToLayer(layerName);
        if (layer < 0)
        {
            return;
        }

        foreach (Transform child in root.GetComponentsInChildren<Transform>(true))
        {
            child.gameObject.layer = layer;
        }
    }

    private void OnDestroy()
    {
        StopGame();
    }
}
