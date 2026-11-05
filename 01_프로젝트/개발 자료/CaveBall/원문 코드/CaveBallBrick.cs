using UnityEngine;

[RequireComponent(typeof(Collider))]
public sealed class CaveBallBrick : MonoBehaviour
{
    private static readonly int ColorId = Shader.PropertyToID("_Color");
    private static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");

    private Renderer _renderer;
    private MaterialPropertyBlock _propertyBlock;
    private bool _isBroken;

    public CaveBallBrickColor BrickColor { get; private set; }
    public bool IsBroken => _isBroken;

    public void Configure(CaveBallBrickColor brickColor)
    {
        BrickColor = brickColor;
        _renderer = GetComponentInChildren<Renderer>(true);
        _propertyBlock = new MaterialPropertyBlock();
        ApplyColor(brickColor == CaveBallBrickColor.Red ? Color.red : Color.blue);
        ResetBrick();
    }

    public bool TryBreak(CaveBallState ballState)
    {
        if (_isBroken || !Matches(ballState))
        {
            return false;
        }

        _isBroken = true;
        gameObject.SetActive(false);
        return true;
    }

    public void ResetBrick()
    {
        _isBroken = false;
        gameObject.SetActive(true);
    }

    private bool Matches(CaveBallState ballState)
    {
        return CaveBallRules.CanBreakBrick(BrickColor, ballState);
    }

    private void ApplyColor(Color color)
    {
        if (_renderer == null)
        {
            return;
        }

        _renderer.GetPropertyBlock(_propertyBlock);
        _propertyBlock.SetColor(ColorId, color);
        _propertyBlock.SetColor(BaseColorId, color);
        _renderer.SetPropertyBlock(_propertyBlock);
    }
}
