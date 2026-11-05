using UnityEngine;
using CellBig.Contents;
using CellBig.Constants;

public class CaveActionContent : IContent
{
    private CaveActionDialog _dialog;
    private CaveActionSettings _settings;
    private GameObject _BGInstance;
    private CaveActionDisplayRig _displayRig;
    private CaveActionGameManager _gameManager;

    protected override void _OnLoadStart()
    {
        _BGInstance = AddressableLoader.Instance.Instantiate("CaveActionBG", transform);
        if (_BGInstance != null)
        {
            _BGInstance.SetActive(false);
        }
        else
        {
            Debug.LogError("[CaveActionContent] CaveActionBG Addressable 생성에 실패했습니다.");
        }
        _SetLoadComplete();
    }

    protected override void _OnLoadComplete()
    {
        const string settingsPath = "Setting/CaveActionSettings.json";
        _settings = _LoadSettings<CaveActionSettings>(settingsPath);
        if (_BGInstance == null)
        {
            return;
        }

        _displayRig = _BGInstance.GetComponent<CaveActionDisplayRig>();
        if (_displayRig == null)
        {
            _displayRig = _BGInstance.AddComponent<CaveActionDisplayRig>();
        }
        _displayRig.Configure(_settings);

        _gameManager = _BGInstance.GetComponent<CaveActionGameManager>();
        if (_gameManager == null)
        {
            _gameManager = _BGInstance.AddComponent<CaveActionGameManager>();
        }
        _gameManager.Initialize(_settings, _displayRig);
    }

    protected override void _OnUILoadComplete()
    {
        _dialog = _GetDialog<CaveActionDialog>(DialogName.CaveActionDialog);
    }

    protected override void _OnUnload()
    {
        _gameManager?.StopGame();
        _displayRig?.DeactivateSession();
        if (_BGInstance != null)
        {
            AddressableLoader.Instance.Destroy(_BGInstance);
        }
    }

    protected override void _OnEnter()
    {
        _dialog?.Show();
        if (_BGInstance != null)
        {
            _BGInstance.SetActive(true);
            _displayRig?.ActivateSession();
            _gameManager?.StartGame();
        }
    }

    protected override void _OnExit()
    {
        _gameManager?.StopGame();
        _displayRig?.DeactivateSession();
        _dialog?.Hide();
        if (_BGInstance != null)
        {
            _BGInstance.SetActive(false);
        }
    }
}
