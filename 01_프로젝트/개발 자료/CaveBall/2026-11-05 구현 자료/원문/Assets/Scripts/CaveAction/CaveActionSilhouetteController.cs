using System.Collections;
using System.Collections.Generic;
using CellBig.Module.RTPoseSeg;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public sealed class CaveActionSilhouetteController : MonoBehaviour
{
    private static readonly int MaskTextureId = Shader.PropertyToID("_MaskTex");
    private static readonly int MirrorXId = Shader.PropertyToID("_MirrorX");
    private static readonly int LeftColorId = Shader.PropertyToID("_LeftColor");
    private static readonly int RightColorId = Shader.PropertyToID("_RightColor");
    private static readonly int ThresholdId = Shader.PropertyToID("_Threshold");
    private static readonly int FeatherId = Shader.PropertyToID("_Feather");
    private static readonly int LeftVisibleId = Shader.PropertyToID("_LeftVisible");
    private static readonly int RightVisibleId = Shader.PropertyToID("_RightVisible");

    private readonly List<CaveActionShatterPiece> _pieces = new();
    private CaveActionSettings _settings;
    private RawImage _silhouette;
    private TMP_Text _gameOverText;
    private Material _silhouetteMaterial;
    private Material _pieceMaterial;
    private Texture _currentMask;
    private RenderTexture _frozenMask;
    private Coroutine _moduleCoroutine;
    private bool _listening;
    private bool _moduleStarted;
    private bool _frozen;

    public bool Initialize(CaveActionSettings settings)
    {
        _settings = settings;
        _silhouette = FindDeepComponent<RawImage>("SilhouetteView");
        _gameOverText = FindDeepComponent<TMP_Text>("GameOverText");
        if (_silhouette == null)
        {
            Debug.LogError("[CaveAction] SilhouetteView RawImage를 찾지 못했습니다.");
            return false;
        }

        Shader silhouetteShader = Resources.Load<Shader>("Shaders/CaveBallSilhouette");
        Shader pieceShader = Resources.Load<Shader>("Shaders/CaveActionMaskTint");
        if (silhouetteShader == null || pieceShader == null)
        {
            Debug.LogError("[CaveAction] 실루엣 셰이더를 찾지 못했습니다.");
            return false;
        }

        _silhouetteMaterial = new Material(silhouetteShader)
        {
            name = "CaveAction Silhouette Runtime Material"
        };
        _silhouetteMaterial.SetColor(LeftColorId, settings.LeftPlayerColor);
        _silhouetteMaterial.SetColor(RightColorId, settings.RightPlayerColor);
        _silhouetteMaterial.SetFloat(MirrorXId, settings.MirrorWebcamX ? 1f : 0f);
        _silhouetteMaterial.SetFloat(ThresholdId, settings.SilhouetteThreshold);
        _silhouetteMaterial.SetFloat(FeatherId, settings.SilhouetteFeather);
        _silhouetteMaterial.SetFloat(LeftVisibleId, 1f);
        _silhouetteMaterial.SetFloat(RightVisibleId, 1f);
        _pieceMaterial = new Material(pieceShader)
        {
            name = "CaveAction Shatter Runtime Material"
        };
        _pieceMaterial.SetFloat(ThresholdId, settings.SilhouetteThreshold);
        _pieceMaterial.SetFloat(FeatherId, settings.SilhouetteFeather);

        _silhouette.texture = Texture2D.whiteTexture;
        _silhouette.material = _silhouetteMaterial;
        _silhouette.raycastTarget = false;
        if (_gameOverText != null)
        {
            _gameOverText.text = "GAME OVER";
            _gameOverText.gameObject.SetActive(false);
        }
        return true;
    }

    public void StartSession()
    {
        ResetVisuals();
        if (_listening) return;

        Message.AddListener<RTSegOutputMsg>(OnSegOutput);
        _listening = true;
        _moduleCoroutine = StartCoroutine(StartModuleWhenReady());
    }

    public void StopSession()
    {
        if (_moduleCoroutine != null)
        {
            StopCoroutine(_moduleCoroutine);
            _moduleCoroutine = null;
        }
        if (_listening)
        {
            Message.RemoveListener<RTSegOutputMsg>(OnSegOutput);
            _listening = false;
        }
        if (_moduleStarted)
        {
            RTPoseSegLease.Release(
                GetInstanceID(),
                pose: false,
                segmentation: true);
            _moduleStarted = false;
        }
    }

    public void PlayGameOver(CaveActionPlayer loser)
    {
        if (_frozen) return;
        _frozen = true;
        FreezeCurrentMask();
        _silhouetteMaterial.SetFloat(
            loser == CaveActionPlayer.Left ? LeftVisibleId : RightVisibleId,
            0f);
        CreateShatterPieces(loser);
        StartCoroutine(ShowGameOverAfterShatter());
    }

    public void ResetVisuals()
    {
        _frozen = false;
        foreach (CaveActionShatterPiece piece in _pieces)
        {
            if (piece != null) Destroy(piece.gameObject);
        }
        _pieces.Clear();

        if (_frozenMask != null)
        {
            _frozenMask.Release();
            Destroy(_frozenMask);
            _frozenMask = null;
        }
        if (_silhouette != null)
        {
            _silhouette.gameObject.SetActive(true);
            _silhouetteMaterial.SetFloat(LeftVisibleId, 1f);
            _silhouetteMaterial.SetFloat(RightVisibleId, 1f);
            if (_currentMask != null) _silhouetteMaterial.SetTexture(MaskTextureId, _currentMask);
        }
        if (_gameOverText != null) _gameOverText.gameObject.SetActive(false);
    }

    private IEnumerator StartModuleWhenReady()
    {
        while (_listening)
        {
            RTPoseSegDataModel model = Model.First<RTPoseSegDataModel>();
            if (model != null && model._isInitialized)
            {
                RTPoseSegLease.Acquire(
                    GetInstanceID(),
                    pose: false,
                    segmentation: true);
                _moduleStarted = true;
                if (model._liveMaskTexture != null) SetMask(model._liveMaskTexture);
                _moduleCoroutine = null;
                yield break;
            }
            yield return null;
        }
    }

    private void OnSegOutput(RTSegOutputMsg message)
    {
        if (!_frozen && message?.mask != null)
        {
            SetMask(message.mask);
        }
    }

    private void SetMask(Texture mask)
    {
        _currentMask = mask;
        _silhouetteMaterial?.SetTexture(MaskTextureId, mask);
    }

    private void FreezeCurrentMask()
    {
        if (_currentMask == null) return;
        _frozenMask = new RenderTexture(
            Mathf.Max(1, _currentMask.width),
            Mathf.Max(1, _currentMask.height),
            0,
            RenderTextureFormat.ARGB32)
        {
            name = "CaveAction Frozen Silhouette"
        };
        _frozenMask.Create();
        Graphics.Blit(_currentMask, _frozenMask);
    }

    private void CreateShatterPieces(CaveActionPlayer loser)
    {
        if (_frozenMask == null || _silhouette == null) return;

        RectTransform sourceRect = _silhouette.rectTransform;
        Rect rect = sourceRect.rect;
        float width = rect.width > 1f ? rect.width : 1920f;
        float height = rect.height > 1f ? rect.height : 1080f;
        int columns = Mathf.Max(2, _settings.ShatterColumns);
        int rows = Mathf.Max(2, _settings.ShatterRows);
        float cellWidth = width / columns;
        float cellHeight = height / rows;

        for (int y = 0; y < rows; y++)
        {
            for (int x = 0; x < columns; x++)
            {
                bool isLeftHalf = (x + 0.5f) / columns < 0.5f;
                if ((loser == CaveActionPlayer.Left) != isLeftHalf)
                {
                    continue;
                }

                GameObject pieceObject = new($"Silhouette Piece {x}-{y}", typeof(RectTransform), typeof(CanvasRenderer), typeof(RawImage));
                RectTransform pieceRect = pieceObject.GetComponent<RectTransform>();
                pieceRect.SetParent(sourceRect.parent, false);
                pieceRect.anchorMin = pieceRect.anchorMax = new Vector2(0.5f, 0.5f);
                pieceRect.sizeDelta = new Vector2(cellWidth + 1f, cellHeight + 1f);
                pieceRect.anchoredPosition = new Vector2(
                    -width * 0.5f + (x + 0.5f) * cellWidth,
                    -height * 0.5f + (y + 0.5f) * cellHeight);

                RawImage image = pieceObject.GetComponent<RawImage>();
                image.texture = _frozenMask;
                image.material = _pieceMaterial;
                image.color = loser == CaveActionPlayer.Left
                    ? _settings.LeftPlayerColor
                    : _settings.RightPlayerColor;
                float sourceX = _settings.MirrorWebcamX
                    ? 1f - (x + 1f) / columns
                    : (float)x / columns;
                image.uvRect = new Rect(sourceX, (float)y / rows, 1f / columns, 1f / rows);
                image.raycastTarget = false;

                Vector2 away = pieceRect.anchoredPosition.normalized;
                Vector2 velocity = away * Random.Range(
                    _settings.ShatterVelocity * 0.6f,
                    _settings.ShatterVelocity * 1.25f);
                velocity += Random.insideUnitCircle * (_settings.ShatterVelocity * 0.35f);
                CaveActionShatterPiece piece = pieceObject.AddComponent<CaveActionShatterPiece>();
                piece.Begin(
                    velocity,
                    Random.Range(-220f, 220f),
                    _settings.ShatterGravity,
                    _settings.ShatterDuration);
                _pieces.Add(piece);
            }
        }
    }

    private IEnumerator ShowGameOverAfterShatter()
    {
        yield return new WaitForSecondsRealtime(_settings.ShatterDuration);
        if (_gameOverText != null) _gameOverText.gameObject.SetActive(true);
    }

    private T FindDeepComponent<T>(string objectName) where T : Component
    {
        foreach (T component in GetComponentsInChildren<T>(true))
        {
            if (component.name == objectName) return component;
        }
        return null;
    }

    private void OnDestroy()
    {
        StopSession();
        ResetVisuals();
        if (_silhouetteMaterial != null) Destroy(_silhouetteMaterial);
        if (_pieceMaterial != null) Destroy(_pieceMaterial);
    }
}

public sealed class CaveActionShatterPiece : MonoBehaviour
{
    private RectTransform _rectTransform;
    private RawImage _image;
    private Vector2 _velocity;
    private float _angularVelocity;
    private float _gravity;
    private float _duration;
    private float _elapsed;

    public void Begin(Vector2 velocity, float angularVelocity, float gravity, float duration)
    {
        _rectTransform = transform as RectTransform;
        _image = GetComponent<RawImage>();
        _velocity = velocity;
        _angularVelocity = angularVelocity;
        _gravity = gravity;
        _duration = Mathf.Max(0.1f, duration);
    }

    private void Update()
    {
        float delta = Time.unscaledDeltaTime;
        _elapsed += delta;
        _velocity.y -= _gravity * delta;
        _rectTransform.anchoredPosition += _velocity * delta;
        _rectTransform.Rotate(0f, 0f, _angularVelocity * delta);
        Color color = _image.color;
        color.a = 1f - Mathf.Clamp01(_elapsed / _duration);
        _image.color = color;
        if (_elapsed >= _duration) Destroy(gameObject);
    }
}
