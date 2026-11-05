using UnityEngine;

public sealed class CaveBallSilhouetteView : MonoBehaviour
{
    private static readonly int MaskTextureId = Shader.PropertyToID("_MaskTex");
    private static readonly int MirrorXId = Shader.PropertyToID("_MirrorX");

    private Camera _frontCamera;
    private GameObject _quad;
    private Material _material;
    private int _silhouetteLayer;

    public void Initialize(Camera frontCamera, CaveBallSetting settings)
    {
        _frontCamera = frontCamera;
        if (_frontCamera == null)
        {
            Debug.LogWarning("[CaveBallSilhouetteView] FrontCamera가 없어 실루엣을 생성하지 않습니다.");
            return;
        }

        Shader shader = Resources.Load<Shader>("Shaders/CaveBallSilhouette");
        if (shader == null)
        {
            shader = Shader.Find("CaveBall/Silhouette");
        }
        if (shader == null)
        {
            Debug.LogError("[CaveBallSilhouetteView] CaveBall/Silhouette 셰이더를 찾지 못했습니다.");
            return;
        }

        _material = new Material(shader)
        {
            name = "CaveBall Silhouette Runtime Material"
        };
        _material.SetFloat(MirrorXId, settings.MirrorPoseX ? 1f : 0f);
        _silhouetteLayer = LayerMask.NameToLayer("UIEffect");
        if (_silhouetteLayer < 0)
        {
            _silhouetteLayer = 9;
        }

        _quad = GameObject.CreatePrimitive(PrimitiveType.Quad);
        _quad.name = "CaveBall User Silhouette";
        _quad.layer = _silhouetteLayer;
        _quad.transform.SetParent(transform, false);

        Collider generatedCollider = _quad.GetComponent<Collider>();
        if (generatedCollider != null)
        {
            Destroy(generatedCollider);
        }

        _quad.GetComponent<Renderer>().sharedMaterial = _material;
        PlaceAtCameraDepth(settings.FrontInteractionDepth);

        int layerMask = 1 << _silhouetteLayer;
        foreach (Camera cameraComponent in transform.root.GetComponentsInChildren<Camera>(true))
        {
            if (cameraComponent == _frontCamera)
            {
                cameraComponent.cullingMask |= layerMask;
            }
            else
            {
                cameraComponent.cullingMask &= ~layerMask;
            }
        }
    }

    public void SetMask(Texture mask)
    {
        if (_material != null && mask != null)
        {
            _material.SetTexture(MaskTextureId, mask);
        }
    }

    private void PlaceAtCameraDepth(float depth)
    {
        float safeDepth = Mathf.Max(_frontCamera.nearClipPlane + 0.1f, depth);
        float height;
        float width;

        if (_frontCamera.orthographic)
        {
            height = _frontCamera.orthographicSize * 2f;
            width = height * _frontCamera.aspect;
        }
        else
        {
            height = 2f * safeDepth * Mathf.Tan(_frontCamera.fieldOfView * 0.5f * Mathf.Deg2Rad);
            width = height * _frontCamera.aspect;
        }

        _quad.transform.position = _frontCamera.transform.position + _frontCamera.transform.forward * safeDepth;
        _quad.transform.rotation = _frontCamera.transform.rotation;
        _quad.transform.localScale = new Vector3(width, height, 1f);
    }

    private void OnDestroy()
    {
        if (_material != null)
        {
            Destroy(_material);
        }
    }
}
