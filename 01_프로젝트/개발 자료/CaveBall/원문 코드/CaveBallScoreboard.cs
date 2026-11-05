using DG.Tweening;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public sealed class CaveBallScoreboard : MonoBehaviour
{
    [SerializeField] private TMP_FontAsset _scoreboardFont;

    private readonly List<Material> _runtimeMaterials = new();
    private RectTransform _redScoreTransform;
    private RectTransform _blueScoreTransform;
    private TMP_Text _redScoreText;
    private TMP_Text _blueScoreText;
    private CaveBallSetting _settings;

    public void Initialize(
        CaveBallSetting settings,
        Camera frontCamera)
    {
        _settings = settings;
        _redScoreText = CreateScore(
            "Red Scoreboard",
            "RED",
            settings.RedScoreColor,
            frontCamera,
            0.25f,
            out _redScoreTransform);
        _blueScoreText = CreateScore(
            "Blue Scoreboard",
            "BLUE",
            settings.BlueScoreColor,
            frontCamera,
            0.75f,
            out _blueScoreTransform);
        SetScores(0, 0);
    }

    public void SetScores(int redScore, int blueScore)
    {
        SetScoreText(_redScoreText, "RED", redScore);
        SetScoreText(_blueScoreText, "BLUE", blueScore);
    }

    public void Increment(CaveBallBrickColor color, int redScore, int blueScore)
    {
        SetScores(redScore, blueScore);
        Shake(color == CaveBallBrickColor.Red ? _redScoreTransform : _blueScoreTransform);
    }

    private TMP_Text CreateScore(
        string objectName,
        string label,
        Color color,
        Camera targetCamera,
        float horizontalAnchor,
        out RectTransform scoreTransform)
    {
        scoreTransform = null;
        if (targetCamera == null)
        {
            Debug.LogWarning($"[CaveBallScoreboard] '{objectName}'용 카메라가 없습니다.");
            return null;
        }

        int layer = LayerMask.NameToLayer("UIEffect");
        GameObject canvasObject = new GameObject(
            objectName,
            typeof(RectTransform),
            typeof(Canvas),
            typeof(CanvasScaler));
        canvasObject.transform.SetParent(transform, false);
        if (layer >= 0)
        {
            canvasObject.layer = layer;
        }

        Canvas canvas = canvasObject.GetComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceCamera;
        canvas.worldCamera = targetCamera;
        canvas.planeDistance = Mathf.Max(targetCamera.nearClipPlane + 0.1f, 1f);
        canvas.targetDisplay = targetCamera.targetDisplay;
        canvas.sortingOrder = 100;

        CanvasScaler scaler = canvasObject.GetComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1920f, 1080f);
        scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
        scaler.matchWidthOrHeight = 0.5f;

        GameObject textObject = new GameObject(
            "Score",
            typeof(RectTransform),
            typeof(CanvasRenderer),
            typeof(TextMeshProUGUI));
        textObject.transform.SetParent(canvasObject.transform, false);
        if (layer >= 0)
        {
            textObject.layer = layer;
        }

        scoreTransform = textObject.GetComponent<RectTransform>();
        scoreTransform.anchorMin = new Vector2(horizontalAnchor, 1f);
        scoreTransform.anchorMax = new Vector2(horizontalAnchor, 1f);
        scoreTransform.pivot = new Vector2(0.5f, 1f);
        scoreTransform.anchoredPosition = new Vector2(0f, -_settings.ScoreboardTopOffset);
        scoreTransform.sizeDelta = new Vector2(900f, 300f);

        TextMeshProUGUI scoreText = textObject.GetComponent<TextMeshProUGUI>();
        if (_scoreboardFont != null)
        {
            scoreText.font = _scoreboardFont;
        }
        scoreText.text = FormatScore(label, 0);
        scoreText.color = color;
        scoreText.fontSize = _settings.ScoreboardFontSize;
        scoreText.fontStyle = FontStyles.Normal;
        scoreText.alignment = TextAlignmentOptions.Center;
        scoreText.lineSpacing = -20f;
        scoreText.enableAutoSizing = true;
        scoreText.fontSizeMin = Mathf.Max(24f, _settings.ScoreboardFontSize * 0.5f);
        scoreText.fontSizeMax = _settings.ScoreboardFontSize;
        scoreText.raycastTarget = false;
        ApplyGlow(scoreText, color);
        return scoreText;
    }

    private void ApplyGlow(TMP_Text scoreText, Color color)
    {
        Material source = scoreText.fontSharedMaterial;
        if (source == null)
        {
            return;
        }

        Material material = new Material(source)
        {
            name = $"{source.name} ({color})"
        };
        material.EnableKeyword("GLOW_ON");
        SetMaterialColor(material, "_OutlineColor", Color.black);
        SetMaterialFloat(material, "_OutlineWidth", 0.18f);
        SetMaterialColor(material, "_GlowColor", new Color(color.r, color.g, color.b, 0.9f));
        SetMaterialFloat(material, "_GlowOffset", 0f);
        SetMaterialFloat(material, "_GlowPower", 0.6f);
        SetMaterialFloat(material, "_GlowOuter", 0.35f);
        scoreText.fontSharedMaterial = material;
        _runtimeMaterials.Add(material);
    }

    private static void SetMaterialColor(Material material, string property, Color value)
    {
        if (material.HasProperty(property))
        {
            material.SetColor(property, value);
        }
    }

    private static void SetMaterialFloat(Material material, string property, float value)
    {
        if (material.HasProperty(property))
        {
            material.SetFloat(property, value);
        }
    }

    private static string FormatScore(string label, int score)
    {
        return $"<size=42%>{label}</size>\n{Mathf.Max(0, score)}";
    }

    private static void SetScoreText(TMP_Text scoreText, string label, int score)
    {
        if (scoreText != null)
        {
            scoreText.text = FormatScore(label, score);
        }
    }

    private void Shake(RectTransform scoreTransform)
    {
        if (scoreTransform == null || _settings == null)
        {
            return;
        }

        scoreTransform.DOKill(false);
        scoreTransform.anchoredPosition = new Vector2(0f, -_settings.ScoreboardTopOffset);
        scoreTransform.localScale = Vector3.one;

        float duration = Mathf.Max(0.01f, _settings.ScoreShakeDuration);
        DOTween.Sequence()
            .SetTarget(scoreTransform)
            .SetUpdate(true)
            .Join(scoreTransform.DOShakeAnchorPos(
                duration,
                _settings.ScoreShakeStrength,
                vibrato: 18,
                randomness: 90f,
                snapping: false,
                fadeOut: true))
            .Join(scoreTransform.DOPunchScale(
                Vector3.one * _settings.ScorePunchScale,
                duration,
                vibrato: 8,
                elasticity: 0.7f))
            .OnComplete(() =>
            {
                if (scoreTransform != null)
                {
                    scoreTransform.anchoredPosition =
                        new Vector2(0f, -_settings.ScoreboardTopOffset);
                    scoreTransform.localScale = Vector3.one;
                }
            });
    }

    private void OnDestroy()
    {
        _redScoreTransform?.DOKill(false);
        _blueScoreTransform?.DOKill(false);
        foreach (Material material in _runtimeMaterials)
        {
            if (material != null)
            {
                Destroy(material);
            }
        }
        _runtimeMaterials.Clear();
    }
}
