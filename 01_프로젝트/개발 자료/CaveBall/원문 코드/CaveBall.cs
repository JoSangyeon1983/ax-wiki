using UnityEngine;

[RequireComponent(typeof(SphereCollider))]
public sealed class CaveBall : MonoBehaviour
{
    private static readonly int ColorId = Shader.PropertyToID("_Color");
    private static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");

    private Rigidbody _rigidbody;
    private Renderer _renderer;
    private GameObject _ballEffect;
    private MaterialPropertyBlock _propertyBlock;
    private CaveBallSetting _settings;
    private CaveBallGameManager _gameManager;
    private PhysicMaterial _bounceMaterial;
    private Vector3 _initialPosition;
    private float _stateRemaining;
    private bool _isConfigured;

    public CaveBallState State { get; private set; } = CaveBallState.White;
    public Vector3 Velocity => _rigidbody != null ? _rigidbody.velocity : Vector3.zero;

    public void Configure(CaveBallSetting settings, CaveBallGameManager gameManager)
    {
        _settings = settings;
        _gameManager = gameManager;
        _initialPosition = transform.position;
        _renderer = GetComponent<Renderer>();
        _ballEffect = FindBallEffect();
        _propertyBlock = new MaterialPropertyBlock();

        EnsurePhysics();
        SetState(CaveBallState.White, 0f);
        _isConfigured = true;
    }

    public void ResetForRound()
    {
        if (!_isConfigured)
        {
            return;
        }

        _rigidbody.position = _initialPosition;
        _rigidbody.rotation = Quaternion.identity;
        _rigidbody.angularVelocity = Vector3.zero;
        SetState(CaveBallState.White, 0f);

        Vector3 initialDirection = new Vector3(1f, 0.65f, 0.8f).normalized;
        _rigidbody.velocity = EnsureMinimumAxes(initialDirection * _settings.BallSpeed);
        _rigidbody.WakeUp();
    }

    public void StopMotion()
    {
        if (_rigidbody == null)
        {
            return;
        }

        _rigidbody.velocity = Vector3.zero;
        _rigidbody.angularVelocity = Vector3.zero;
        _rigidbody.Sleep();
    }

    public bool TryApplyHandColor(CaveBallState handColor)
    {
        if (!CaveBallRules.CanApplyHandColor(State, handColor))
        {
            return false;
        }

        SetState(handColor, _settings.HandColorDuration);
        return true;
    }

    public void BounceFromFloorContact(Vector2 awayDirection)
    {
        if (!_isConfigured)
        {
            return;
        }

        if (awayDirection.sqrMagnitude < 0.0001f)
        {
            awayDirection = new Vector2(-_rigidbody.velocity.x, -_rigidbody.velocity.z);
        }
        if (awayDirection.sqrMagnitude < 0.0001f)
        {
            awayDirection = Vector2.up;
        }

        awayDirection.Normalize();
        float horizontalSpeed = Mathf.Min(
            _settings.MaximumBallSpeed,
            Mathf.Max(_settings.BallSpeed, _rigidbody.velocity.magnitude) *
            _settings.FloorBounceAcceleration);
        float verticalVelocity = Mathf.Max(
            Mathf.Abs(_rigidbody.velocity.y),
            _settings.MinimumAxisSpeed);

        _rigidbody.velocity = EnsureMinimumAxes(new Vector3(
            awayDirection.x * horizontalSpeed,
            verticalVelocity,
            awayDirection.y * horizontalSpeed));
        _rigidbody.WakeUp();
    }

    private void Update()
    {
        if (!_isConfigured || _stateRemaining <= 0f)
        {
            return;
        }

        _stateRemaining -= Time.deltaTime;
        if (_stateRemaining > 0f)
        {
            return;
        }

        if (State == CaveBallState.Red || State == CaveBallState.Blue)
        {
            SetState(CaveBallState.White, 0f);
        }
    }

    private void FixedUpdate()
    {
        if (!_isConfigured || _rigidbody.IsSleeping())
        {
            return;
        }

        float speed = _rigidbody.velocity.magnitude;
        if (speed < 0.1f)
        {
            _rigidbody.velocity = EnsureMinimumAxes(Vector3.forward * _settings.BallSpeed);
            return;
        }

        float targetSpeed = Mathf.Clamp(
            speed,
            _settings.BallSpeed,
            _settings.MaximumBallSpeed);
        _rigidbody.velocity = EnsureMinimumAxes(_rigidbody.velocity.normalized * targetSpeed);
    }

    private void OnCollisionEnter(Collision collision)
    {
        if (!_isConfigured)
        {
            return;
        }

        CaveBallBrick brick = collision.collider.GetComponentInParent<CaveBallBrick>();
        if (brick != null && brick.TryBreak(State))
        {
            _gameManager.NotifyBrickDestroyed(brick);
        }
    }

    private void EnsurePhysics()
    {
        _rigidbody = GetComponent<Rigidbody>();
        if (_rigidbody == null)
        {
            _rigidbody = gameObject.AddComponent<Rigidbody>();
        }

        _rigidbody.useGravity = false;
        _rigidbody.mass = 1f;
        _rigidbody.drag = 0f;
        _rigidbody.angularDrag = 0.05f;
        _rigidbody.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
        _rigidbody.interpolation = RigidbodyInterpolation.Interpolate;

        SphereCollider sphereCollider = GetComponent<SphereCollider>();
        if (_bounceMaterial != null)
        {
            Destroy(_bounceMaterial);
        }

        _bounceMaterial = new PhysicMaterial("CaveBall Runtime Bounce")
        {
            bounciness = 1f,
            dynamicFriction = 0f,
            staticFriction = 0f,
            bounceCombine = PhysicMaterialCombine.Maximum,
            frictionCombine = PhysicMaterialCombine.Minimum
        };
        sphereCollider.sharedMaterial = _bounceMaterial;

        int ballLayer = LayerMask.NameToLayer("Ball");
        if (ballLayer >= 0)
        {
            gameObject.layer = ballLayer;
        }
    }

    private Vector3 EnsureMinimumAxes(Vector3 velocity)
    {
        float min = _settings.MinimumAxisSpeed;
        velocity.x = EnsureAxis(velocity.x, min, 1f);
        velocity.y = EnsureAxis(velocity.y, min, 1f);
        velocity.z = EnsureAxis(velocity.z, min, 1f);
        return velocity;
    }

    private static float EnsureAxis(float value, float minimum, float fallbackSign)
    {
        if (Mathf.Abs(value) >= minimum)
        {
            return value;
        }

        float sign = Mathf.Abs(value) > 0.001f ? Mathf.Sign(value) : fallbackSign;
        return sign * minimum;
    }

    private void SetState(CaveBallState newState, float duration)
    {
        State = newState;
        _stateRemaining = Mathf.Max(0f, duration);
        ApplyColor(GetStateColor(newState));
        SetBallEffectVisible(newState != CaveBallState.White);
    }

    private void ApplyColor(Color color)
    {
        if (_renderer == null)
        {
            return;
        }

        CellBig.SoundManager.Instance.PlaySound(CellBig.SoundType.Explosion_Electro01);

        _renderer.GetPropertyBlock(_propertyBlock);
        _propertyBlock.SetColor(ColorId, color);
        _propertyBlock.SetColor(BaseColorId, color);
        _renderer.SetPropertyBlock(_propertyBlock);
    }

    private static Color GetStateColor(CaveBallState state)
    {
        switch (state)
        {
            case CaveBallState.Yellow:
                return Color.yellow;
            case CaveBallState.Red:
                return Color.red;
            case CaveBallState.Blue:
                return Color.blue;
            default:
                return Color.white;
        }
    }

    private GameObject FindBallEffect()
    {
        ParticleSystem fallback = null;
        foreach (ParticleSystem particles in GetComponentsInChildren<ParticleSystem>(true))
        {
            if (particles.transform == transform)
            {
                continue;
            }

            if (fallback == null)
            {
                fallback = particles;
            }

            if (particles.name == "Effect" || particles.name == "launcher")
            {
                return GetDirectChildRoot(particles.transform).gameObject;
            }
        }

        return fallback != null ? GetDirectChildRoot(fallback.transform).gameObject : null;
    }

    private Transform GetDirectChildRoot(Transform child)
    {
        Transform current = child;
        while (current.parent != null && current.parent != transform)
        {
            current = current.parent;
        }
        return current;
    }

    private void SetBallEffectVisible(bool visible)
    {
        if (_ballEffect == null)
        {
            return;
        }

        _ballEffect.SetActive(visible);
        foreach (ParticleSystem particles in _ballEffect.GetComponentsInChildren<ParticleSystem>(true))
        {
            if (visible)
            {
                particles.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
                particles.Play(true);
            }
            else
            {
                particles.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            }
        }
    }

    private void OnDestroy()
    {
        if (_bounceMaterial != null)
        {
            Destroy(_bounceMaterial);
            _bounceMaterial = null;
        }
    }
}
