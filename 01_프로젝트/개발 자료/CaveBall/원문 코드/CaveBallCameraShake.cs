using DG.Tweening;
using UnityEngine;

public sealed class CaveBallCameraShake : MonoBehaviour
{
    private Vector3 _baseLocalPosition;
    private Quaternion _baseLocalRotation;
    private Sequence _shakeSequence;

    private void Awake()
    {
        _baseLocalPosition = transform.localPosition;
        _baseLocalRotation = transform.localRotation;
    }

    public void Shake(float duration, float positionMagnitude, float rotationMagnitude)
    {
        StopShake();
        float safeDuration = Mathf.Max(0.01f, duration);

        Tween positionShake = transform.DOShakePosition(
            safeDuration,
            new Vector3(positionMagnitude, positionMagnitude, 0f),
            vibrato: 14,
            randomness: 90f,
            snapping: false,
            fadeOut: true);
        Tween rotationShake = transform.DOShakeRotation(
            safeDuration,
            new Vector3(rotationMagnitude, rotationMagnitude, rotationMagnitude * 0.5f),
            vibrato: 14,
            randomness: 90f,
            fadeOut: true);

        _shakeSequence = DOTween.Sequence()
            .SetUpdate(UpdateType.Late, true)
            .Join(positionShake)
            .Join(rotationShake)
            .OnComplete(() =>
            {
                Restore();
                _shakeSequence = null;
            });
    }

    private void Restore()
    {
        transform.localPosition = _baseLocalPosition;
        transform.localRotation = _baseLocalRotation;
    }

    private void StopShake()
    {
        if (_shakeSequence != null && _shakeSequence.IsActive())
        {
            _shakeSequence.Kill(false);
        }
        _shakeSequence = null;
        Restore();
    }

    private void OnDisable()
    {
        StopShake();
    }

    private void OnDestroy()
    {
        StopShake();
    }
}
