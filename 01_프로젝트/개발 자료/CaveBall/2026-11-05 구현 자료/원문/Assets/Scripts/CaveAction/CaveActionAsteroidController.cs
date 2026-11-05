using System.Collections.Generic;
using CellBig;
using UnityEngine;

public sealed class CaveActionAsteroidController : MonoBehaviour
{
    private const int MaximumBigAsteroids = 4;

    private enum AsteroidSize
    {
        Big,
        Mid,
        Small
    }

    private sealed class ActiveAsteroid
    {
        public GameObject Instance;
        public Rigidbody Body;
        public SphereCollider Collider;
        public AsteroidSize Size;
        public float Radius;
        public float SpawnedAt;
        public bool Entering;
        public Vector3 EntryStart;
        public Vector3 EntryTarget;
        public Vector3 EntryVelocity;
        public Vector3 EntryAngularVelocity;
        public float EntryStartedAt;
    }

    private readonly List<ActiveAsteroid> _asteroids = new();
    private readonly List<BoxCollider> _xWalls = new();
    private readonly List<BoxCollider> _yWalls = new();
    private readonly List<BoxCollider> _zWalls = new();

    private CaveActionSettings _settings;
    private Transform _wallRoot;
    private Transform _instancesRoot;
    private GameObject[] _bigTemplates;
    private GameObject[] _midTemplates;
    private GameObject[] _smallTemplates;
    private GameObject _breakTemplate;
    private PhysicMaterial _physicsMaterial;
    private int _effectLayer;
    private float _minimumX;
    private float _maximumX;
    private float _minimumZ;
    private float _maximumZ;
    private float _fixedY;
    private float _nextSpawnAt;
    private bool _running;

    public bool Initialize(
        CaveActionSettings settings,
        Transform wallRoot,
        GameObject[] bigTemplates,
        GameObject[] midTemplates,
        GameObject[] smallTemplates,
        GameObject breakTemplate,
        int effectLayer)
    {
        _settings = settings;
        _wallRoot = wallRoot;
        _bigTemplates = bigTemplates;
        _midTemplates = midTemplates;
        _smallTemplates = smallTemplates;
        _breakTemplate = breakTemplate;
        _effectLayer = effectLayer;

        if (_settings == null || _wallRoot == null ||
            !HasAllTemplates(_bigTemplates) ||
            !HasAllTemplates(_midTemplates) ||
            !HasAllTemplates(_smallTemplates) ||
            _breakTemplate == null)
        {
            Debug.LogError("[CaveActionAsteroid] 소행성 템플릿 또는 AsteroidWall이 누락되었습니다.");
            return false;
        }

        GameObject root = new("Asteroid Instances");
        root.transform.SetParent(transform, false);
        _instancesRoot = root.transform;
        _physicsMaterial = new PhysicMaterial("CaveAction Asteroid Physics")
        {
            dynamicFriction = 0f,
            staticFriction = 0f,
            bounciness = 1f,
            frictionCombine = PhysicMaterialCombine.Minimum,
            bounceCombine = PhysicMaterialCombine.Maximum
        };

        if (!AlignAndMeasureWall())
        {
            Debug.LogError("[CaveActionAsteroid] AsteroidWall의 경계 Collider를 판별하지 못했습니다.");
            return false;
        }
        SetLayerRecursively(_wallRoot, _effectLayer);
        return true;
    }

    public void ResetSession()
    {
        Clear();
        _running = true;
        int initialCount = Mathf.Clamp(
            _settings.AsteroidInitialCount,
            0,
            Mathf.Min(
                MaximumBigAsteroids,
                Mathf.Max(1, _settings.AsteroidMaximumCount)));
        for (int i = 0; i < initialCount; i++)
        {
            SpawnAsteroid(AsteroidSize.Big, null, null);
        }
        _nextSpawnAt = Time.unscaledTime + Mathf.Max(0.1f, _settings.AsteroidSpawnInterval);
    }

    public void PauseSession()
    {
        _running = false;
        foreach (ActiveAsteroid asteroid in _asteroids)
        {
            if (asteroid?.Body == null) continue;
            asteroid.Body.velocity = Vector3.zero;
            asteroid.Body.angularVelocity = Vector3.zero;
            asteroid.Body.isKinematic = true;
        }
    }

    public void StopSession()
    {
        _running = false;
        Clear();
    }

    public void CheckContacts(IReadOnlyList<Rect> normalizedContacts)
    {
        if (!_running || normalizedContacts == null || normalizedContacts.Count == 0) return;

        int originalCount = _asteroids.Count;
        for (int index = originalCount - 1; index >= 0; index--)
        {
            if (index >= _asteroids.Count) continue;
            ActiveAsteroid asteroid = _asteroids[index];
            if (!CanBeHit(asteroid)) continue;

            Rect asteroidRect = GetNormalizedRect(asteroid);
            for (int contactIndex = 0; contactIndex < normalizedContacts.Count; contactIndex++)
            {
                if (!asteroidRect.Overlaps(normalizedContacts[contactIndex])) continue;
                SplitAsteroid(index);
                break;
            }
        }
    }

    public void HitByLaser(IReadOnlyList<Vector3> path, bool crossesFrontFloor)
    {
        if (!_running || path == null || path.Count < 2) return;

        int originalCount = _asteroids.Count;
        for (int index = originalCount - 1; index >= 0; index--)
        {
            if (index >= _asteroids.Count) continue;
            ActiveAsteroid asteroid = _asteroids[index];
            if (!CanBeHit(asteroid)) continue;

            float hitRadius = asteroid.Radius + Mathf.Max(0f, _settings.AsteroidLaserHitRadius);
            bool hit = crossesFrontFloor
                ? path.Count >= 4 &&
                  DistanceToSegment(asteroid.Body.position, path[2], path[3]) <= hitRadius
                : IsNearAnySegment(asteroid.Body.position, path, hitRadius);
            if (hit) SplitAsteroid(index);
        }
    }

    private void Update()
    {
        if (!_running || _settings == null) return;
        UpdateEnteringAsteroids();
        if (Time.unscaledTime < _nextSpawnAt) return;

        _nextSpawnAt = Time.unscaledTime + Mathf.Max(0.1f, _settings.AsteroidSpawnInterval);
        if (_asteroids.Count < Mathf.Max(1, _settings.AsteroidMaximumCount) &&
            CountAsteroids(AsteroidSize.Big) < MaximumBigAsteroids)
        {
            SpawnAsteroid(AsteroidSize.Big, null, null);
        }
    }

    private bool AlignAndMeasureWall()
    {
        Transform colliderRoot = _wallRoot.Find("Collider");
        if (colliderRoot == null) return false;

        BoxCollider[] colliders = colliderRoot.GetComponentsInChildren<BoxCollider>(true);
        if (colliders.Length < 4) return false;

        Bounds bounds = CalculateWorldBounds(colliders[0]);
        for (int i = 1; i < colliders.Length; i++)
        {
            bounds.Encapsulate(CalculateWorldBounds(colliders[i]));
        }

        Vector3 minimum = _settings.ArenaCenter - _settings.ArenaSize * 0.5f;
        Vector3 targetCenter = new(
            _settings.ArenaCenter.x,
            minimum.y + Mathf.Max(0f, _settings.WorldEffectSurfaceOffset),
            _settings.ArenaCenter.z);
        _wallRoot.position += targetCenter - bounds.center;
        Dictionary<BoxCollider, Bounds> colliderBounds = new(colliders.Length);
        foreach (BoxCollider collider in colliders)
        {
            colliderBounds.Add(collider, CalculateWorldBounds(collider));
        }

        _xWalls.Clear();
        _yWalls.Clear();
        _zWalls.Clear();
        foreach (BoxCollider collider in colliders)
        {
            Vector3 size = colliderBounds[collider].size;
            if (size.x <= size.y && size.x <= size.z) _xWalls.Add(collider);
            else if (size.y <= size.x && size.y <= size.z) _yWalls.Add(collider);
            else _zWalls.Add(collider);
        }

        if (_xWalls.Count < 2 || _zWalls.Count < 2) return false;
        _xWalls.Sort((left, right) =>
            colliderBounds[left].center.x.CompareTo(colliderBounds[right].center.x));
        _yWalls.Sort((left, right) =>
            colliderBounds[left].center.y.CompareTo(colliderBounds[right].center.y));
        _zWalls.Sort((left, right) =>
            colliderBounds[left].center.z.CompareTo(colliderBounds[right].center.z));

        _minimumX = colliderBounds[_xWalls[0]].max.x;
        _maximumX = colliderBounds[_xWalls[_xWalls.Count - 1]].min.x;
        _minimumZ = colliderBounds[_zWalls[0]].max.z;
        _maximumZ = colliderBounds[_zWalls[_zWalls.Count - 1]].min.z;
        _fixedY = _yWalls.Count >= 2
            ? (colliderBounds[_yWalls[0]].max.y +
               colliderBounds[_yWalls[_yWalls.Count - 1]].min.y) * 0.5f
            : targetCenter.y;
        return _maximumX > _minimumX && _maximumZ > _minimumZ;
    }

    private static Bounds CalculateWorldBounds(BoxCollider collider)
    {
        Vector3 halfSize = collider.size * 0.5f;
        Vector3 firstCorner = collider.transform.TransformPoint(
            collider.center - halfSize);
        Bounds bounds = new(firstCorner, Vector3.zero);
        for (int x = -1; x <= 1; x += 2)
        {
            for (int y = -1; y <= 1; y += 2)
            {
                for (int z = -1; z <= 1; z += 2)
                {
                    Vector3 localCorner = collider.center + Vector3.Scale(
                        halfSize,
                        new Vector3(x, y, z));
                    bounds.Encapsulate(collider.transform.TransformPoint(localCorner));
                }
            }
        }
        return bounds;
    }

    private ActiveAsteroid SpawnAsteroid(
        AsteroidSize size,
        Vector3? requestedPosition,
        Vector3? inheritedVelocity)
    {
        if (_asteroids.Count >= Mathf.Max(1, _settings.AsteroidMaximumCount)) return null;
        if (size == AsteroidSize.Big &&
            CountAsteroids(AsteroidSize.Big) >= MaximumBigAsteroids)
        {
            return null;
        }

        GameObject template = GetRandomTemplate(size);
        GameObject instance = Instantiate(template, _instancesRoot);
        instance.name = $"{size} Asteroid";
        SetLayerRecursively(instance.transform, _effectLayer);
        instance.transform.position = new Vector3(
            (_minimumX + _maximumX) * 0.5f,
            _fixedY,
            (_minimumZ + _maximumZ) * 0.5f);
        instance.transform.rotation = Random.rotationUniform;

        foreach (Collider existingCollider in instance.GetComponentsInChildren<Collider>(true))
        {
            existingCollider.enabled = false;
        }
        foreach (Rigidbody existingBody in instance.GetComponentsInChildren<Rigidbody>(true))
        {
            if (existingBody.gameObject != instance) existingBody.isKinematic = true;
        }

        instance.SetActive(true);
        Bounds visualBounds = CalculateRendererBounds(instance);
        float worldRadius = Mathf.Max(0.1f, Mathf.Max(visualBounds.extents.x, visualBounds.extents.z)) *
                            Mathf.Clamp(_settings.AsteroidColliderScale, 0.1f, 1f);
        float maximumScale = Mathf.Max(
            0.0001f,
            Mathf.Max(
                Mathf.Abs(instance.transform.lossyScale.x),
                Mathf.Max(
                    Mathf.Abs(instance.transform.lossyScale.y),
                    Mathf.Abs(instance.transform.lossyScale.z))));

        SphereCollider sphere = instance.AddComponent<SphereCollider>();
        sphere.center = instance.transform.InverseTransformPoint(visualBounds.center);
        sphere.radius = worldRadius / maximumScale;
        sphere.material = _physicsMaterial;

        Vector3 targetPosition = requestedPosition ?? RandomPosition(worldRadius);
        targetPosition.x = Mathf.Clamp(
            targetPosition.x,
            _minimumX + worldRadius,
            _maximumX - worldRadius);
        targetPosition.y = _fixedY;
        targetPosition.z = Mathf.Clamp(
            targetPosition.z,
            _minimumZ + worldRadius,
            _maximumZ - worldRadius);
        bool entersFromOutside = size == AsteroidSize.Big && !requestedPosition.HasValue;
        Vector3 startPosition = entersFromOutside
            ? RandomOutsidePosition(targetPosition, worldRadius)
            : targetPosition;
        instance.transform.position = startPosition;

        Rigidbody body = instance.AddComponent<Rigidbody>();
        body.useGravity = false;
        body.mass = GetMass(size);
        body.drag = 0f;
        body.angularDrag = 0f;
        body.interpolation = RigidbodyInterpolation.Interpolate;
        body.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
        body.constraints = RigidbodyConstraints.FreezePositionY |
                           RigidbodyConstraints.FreezeRotationX |
                           RigidbodyConstraints.FreezeRotationZ;
        body.sleepThreshold = 0f;
        body.isKinematic = entersFromOutside;
        sphere.enabled = !entersFromOutside;

        Vector3 velocity = inheritedVelocity ?? RandomVelocity();
        velocity.y = 0f;
        if (velocity.sqrMagnitude < 0.01f) velocity = Vector3.right * _settings.AsteroidMinimumSpeed;
        Vector3 angularVelocity = new(
            0f,
            Random.Range(
                -Mathf.Abs(_settings.AsteroidMaximumAngularSpeed),
                Mathf.Abs(_settings.AsteroidMaximumAngularSpeed)) * Mathf.Deg2Rad,
            0f);
        if (!entersFromOutside)
        {
            body.velocity = velocity;
            body.angularVelocity = angularVelocity;
        }

        ActiveAsteroid asteroid = new()
        {
            Instance = instance,
            Body = body,
            Collider = sphere,
            Size = size,
            Radius = worldRadius,
            SpawnedAt = Time.unscaledTime,
            Entering = entersFromOutside,
            EntryStart = startPosition,
            EntryTarget = targetPosition,
            EntryVelocity = velocity,
            EntryAngularVelocity = angularVelocity,
            EntryStartedAt = Time.unscaledTime
        };
        _asteroids.Add(asteroid);
        return asteroid;
    }

    private void UpdateEnteringAsteroids()
    {
        float duration = Mathf.Max(0.1f, _settings.AsteroidEntryDuration);
        foreach (ActiveAsteroid asteroid in _asteroids)
        {
            if (asteroid == null || !asteroid.Entering ||
                asteroid.Instance == null || asteroid.Body == null)
            {
                continue;
            }

            float progress = Mathf.Clamp01(
                (Time.unscaledTime - asteroid.EntryStartedAt) / duration);
            float eased = progress * progress * (3f - 2f * progress);
            asteroid.Body.position = Vector3.Lerp(
                asteroid.EntryStart,
                asteroid.EntryTarget,
                eased);
            asteroid.Instance.transform.Rotate(
                Vector3.up,
                asteroid.EntryAngularVelocity.y * Mathf.Rad2Deg * Time.unscaledDeltaTime,
                Space.World);

            if (progress < 1f) continue;
            asteroid.Body.position = asteroid.EntryTarget;
            asteroid.Body.isKinematic = false;
            asteroid.Collider.enabled = true;
            asteroid.Body.velocity = asteroid.EntryVelocity;
            asteroid.Body.angularVelocity = asteroid.EntryAngularVelocity;
            asteroid.SpawnedAt = Time.unscaledTime;
            asteroid.Entering = false;
        }
    }

    private void SplitAsteroid(int index)
    {
        if (index < 0 || index >= _asteroids.Count) return;
        ActiveAsteroid source = _asteroids[index];
        _asteroids.RemoveAt(index);

        Vector3 position = source.Body != null ? source.Body.position : source.Instance.transform.position;
        Vector3 velocity = source.Body != null ? source.Body.velocity : Vector3.zero;
        float radius = source.Radius;
        AsteroidSize sourceSize = source.Size;
        SpawnBreakEffect(position);
        SoundManager.Instance.PlaySound(SoundType.Explosion_FireBlazing03);
        if (source.Instance != null)
        {
            source.Instance.SetActive(false);
            Destroy(source.Instance);
        }

        if (sourceSize == AsteroidSize.Small) return;
        AsteroidSize childSize = sourceSize == AsteroidSize.Big
            ? AsteroidSize.Mid
            : AsteroidSize.Small;
        int minimumChildren = Mathf.Max(1, _settings.AsteroidMinimumSplitCount);
        int maximumChildren = Mathf.Max(minimumChildren, _settings.AsteroidMaximumSplitCount);
        int childCount = Random.Range(minimumChildren, maximumChildren + 1);
        for (int childIndex = 0; childIndex < childCount; childIndex++)
        {
            if (_asteroids.Count >= Mathf.Max(1, _settings.AsteroidMaximumCount)) break;
            float angle = (360f / childCount) * childIndex + Random.Range(-25f, 25f);
            Vector3 direction = Quaternion.Euler(0f, angle, 0f) * Vector3.right;
            Vector3 childPosition = position + direction * radius * 0.22f;
            Vector3 childVelocity = velocity * 0.45f +
                                    direction * Random.Range(
                                        _settings.AsteroidMinimumSpeed,
                                        _settings.AsteroidMaximumSpeed);
            SpawnAsteroid(childSize, childPosition, childVelocity);
        }
    }

    private void SpawnBreakEffect(Vector3 position)
    {
        GameObject effect = Instantiate(_breakTemplate, _instancesRoot);
        effect.name = "Asteroid Break Effect";
        SetLayerRecursively(effect.transform, _effectLayer);
        effect.transform.position = position;
        foreach (Collider collider in effect.GetComponentsInChildren<Collider>(true))
        {
            collider.enabled = false;
        }
        effect.SetActive(true);
        foreach (ParticleSystem particles in effect.GetComponentsInChildren<ParticleSystem>(true))
        {
            particles.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            particles.Play(true);
        }
        Destroy(effect, Mathf.Max(0.1f, _settings.ImpactEffectLifetime));
    }

    private int CountAsteroids(AsteroidSize size)
    {
        int count = 0;
        foreach (ActiveAsteroid asteroid in _asteroids)
        {
            if (asteroid != null && asteroid.Size == size) count++;
        }
        return count;
    }

    private Rect GetNormalizedRect(ActiveAsteroid asteroid)
    {
        Vector3 position = asteroid.Body != null
            ? asteroid.Body.position
            : asteroid.Instance.transform.position;
        float width = Mathf.Max(0.0001f, _maximumX - _minimumX);
        float height = Mathf.Max(0.0001f, _maximumZ - _minimumZ);
        Vector2 center = new(
            Mathf.InverseLerp(_minimumX, _maximumX, position.x),
            Mathf.InverseLerp(_minimumZ, _maximumZ, position.z));
        Vector2 size = new(
            asteroid.Radius * 2f / width,
            asteroid.Radius * 2f / height);
        return new Rect(center - size * 0.5f, size);
    }

    private bool CanBeHit(ActiveAsteroid asteroid)
    {
        return asteroid?.Instance != null &&
               asteroid.Body != null &&
               !asteroid.Entering &&
               Time.unscaledTime - asteroid.SpawnedAt >=
               Mathf.Max(0f, _settings.AsteroidSplitGraceDuration);
    }

    private Vector3 RandomOutsidePosition(Vector3 target, float radius)
    {
        float distance = radius + Mathf.Max(0.1f, _settings.AsteroidEntryOutsideDistance);
        float horizontalJitter = (_maximumX - _minimumX) * 0.2f;
        float verticalJitter = (_maximumZ - _minimumZ) * 0.2f;
        Vector3 result = target;
        switch (Random.Range(0, 4))
        {
            case 0:
                result.x = _minimumX - distance;
                result.z = Mathf.Clamp(
                    target.z + Random.Range(-verticalJitter, verticalJitter),
                    _minimumZ,
                    _maximumZ);
                break;
            case 1:
                result.x = _maximumX + distance;
                result.z = Mathf.Clamp(
                    target.z + Random.Range(-verticalJitter, verticalJitter),
                    _minimumZ,
                    _maximumZ);
                break;
            case 2:
                result.z = _minimumZ - distance;
                result.x = Mathf.Clamp(
                    target.x + Random.Range(-horizontalJitter, horizontalJitter),
                    _minimumX,
                    _maximumX);
                break;
            default:
                result.z = _maximumZ + distance;
                result.x = Mathf.Clamp(
                    target.x + Random.Range(-horizontalJitter, horizontalJitter),
                    _minimumX,
                    _maximumX);
                break;
        }
        result.y = _fixedY;
        return result;
    }

    private Vector3 RandomPosition(float radius)
    {
        float minimumX = _minimumX + radius;
        float maximumX = _maximumX - radius;
        float minimumZ = _minimumZ + radius;
        float maximumZ = _maximumZ - radius;
        return new Vector3(
            minimumX < maximumX ? Random.Range(minimumX, maximumX) : (_minimumX + _maximumX) * 0.5f,
            _fixedY,
            minimumZ < maximumZ ? Random.Range(minimumZ, maximumZ) : (_minimumZ + _maximumZ) * 0.5f);
    }

    private Vector3 RandomVelocity()
    {
        Vector2 direction = Random.insideUnitCircle.normalized;
        if (direction.sqrMagnitude < 0.001f) direction = Vector2.right;
        float minimumSpeed = Mathf.Max(0.01f, _settings.AsteroidMinimumSpeed);
        float maximumSpeed = Mathf.Max(minimumSpeed, _settings.AsteroidMaximumSpeed);
        return new Vector3(direction.x, 0f, direction.y) *
               Random.Range(minimumSpeed, maximumSpeed);
    }

    private GameObject GetRandomTemplate(AsteroidSize size)
    {
        GameObject[] templates = size switch
        {
            AsteroidSize.Big => _bigTemplates,
            AsteroidSize.Mid => _midTemplates,
            _ => _smallTemplates
        };
        return templates[Random.Range(0, templates.Length)];
    }

    private static float GetMass(AsteroidSize size)
    {
        return size switch
        {
            AsteroidSize.Big => 3f,
            AsteroidSize.Mid => 1.5f,
            _ => 0.75f
        };
    }

    private static Bounds CalculateRendererBounds(GameObject instance)
    {
        Renderer[] renderers = instance.GetComponentsInChildren<Renderer>(true);
        if (renderers.Length == 0)
        {
            return new Bounds(instance.transform.position, Vector3.one);
        }

        Bounds bounds = renderers[0].bounds;
        for (int i = 1; i < renderers.Length; i++) bounds.Encapsulate(renderers[i].bounds);
        return bounds;
    }

    private static bool IsNearAnySegment(
        Vector3 point,
        IReadOnlyList<Vector3> path,
        float radius)
    {
        for (int i = 1; i < path.Count; i++)
        {
            if (DistanceToSegment(point, path[i - 1], path[i]) <= radius) return true;
        }
        return false;
    }

    private static float DistanceToSegment(Vector3 point, Vector3 from, Vector3 to)
    {
        Vector3 segment = to - from;
        float lengthSquared = segment.sqrMagnitude;
        if (lengthSquared <= 0.0001f) return Vector3.Distance(point, from);
        float progress = Mathf.Clamp01(Vector3.Dot(point - from, segment) / lengthSquared);
        return Vector3.Distance(point, from + segment * progress);
    }

    private static bool HasAllTemplates(GameObject[] templates)
    {
        if (templates == null || templates.Length == 0) return false;
        foreach (GameObject template in templates)
        {
            if (template == null) return false;
        }
        return true;
    }

    private static void SetLayerRecursively(Transform root, int layer)
    {
        root.gameObject.layer = layer;
        foreach (Transform child in root)
        {
            SetLayerRecursively(child, layer);
        }
    }

    private void Clear()
    {
        foreach (ActiveAsteroid asteroid in _asteroids)
        {
            if (asteroid?.Instance != null) Destroy(asteroid.Instance);
        }
        _asteroids.Clear();
    }

    private void OnDestroy()
    {
        Clear();
        if (_physicsMaterial != null) Destroy(_physicsMaterial);
    }
}
