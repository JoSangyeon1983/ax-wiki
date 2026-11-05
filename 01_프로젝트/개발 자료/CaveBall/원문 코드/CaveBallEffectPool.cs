using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public sealed class CaveBallEffectPool : MonoBehaviour
{
    private readonly Queue<GameObject> _available = new();
    private readonly HashSet<GameObject> _active = new();

    private GameObject _template;
    private float _effectDuration;
    private int _effectLayer;

    public void Initialize(
        GameObject template,
        int initialSize,
        float effectDuration,
        string layerName)
    {
        _template = template;
        _effectDuration = Mathf.Max(0.1f, effectDuration);
        _effectLayer = LayerMask.NameToLayer(layerName);

        if (_template == null)
        {
            return;
        }

        _template.SetActive(false);
        for (int i = 0; i < Mathf.Max(1, initialSize); i++)
        {
            _available.Enqueue(CreateInstance());
        }
    }

    public void Play(Vector3 worldPosition)
    {
        if (_template == null)
        {
            return;
        }

        GameObject instance = _available.Count > 0 ? _available.Dequeue() : CreateInstance();
        instance.transform.SetPositionAndRotation(worldPosition, _template.transform.rotation);
        instance.SetActive(true);

        foreach (ParticleSystem particles in instance.GetComponentsInChildren<ParticleSystem>(true))
        {
            particles.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            particles.Play(true);
        }

        _active.Add(instance);
        StartCoroutine(ReturnAfterDelay(instance));
    }

    public void StopAll()
    {
        StopAllCoroutines();
        foreach (GameObject instance in _active)
        {
            ReturnToPool(instance);
        }
        _active.Clear();
    }

    private GameObject CreateInstance()
    {
        GameObject instance = Instantiate(_template, transform);
        instance.name = $"{_template.name} (Pooled)";
        instance.SetActive(false);

        if (_effectLayer >= 0)
        {
            foreach (Transform child in instance.GetComponentsInChildren<Transform>(true))
            {
                child.gameObject.layer = _effectLayer;
            }
        }

        return instance;
    }

    private IEnumerator ReturnAfterDelay(GameObject instance)
    {
        yield return new WaitForSeconds(_effectDuration);
        if (_active.Remove(instance))
        {
            ReturnToPool(instance);
        }
    }

    private void ReturnToPool(GameObject instance)
    {
        if (instance == null)
        {
            return;
        }

        foreach (ParticleSystem particles in instance.GetComponentsInChildren<ParticleSystem>(true))
        {
            particles.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
        }
        instance.SetActive(false);
        _available.Enqueue(instance);
    }

    private void OnDisable()
    {
        StopAll();
    }
}
