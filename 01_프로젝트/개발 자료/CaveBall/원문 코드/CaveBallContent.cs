using UnityEngine;
using CellBig.Contents;
using CellBig.Constants;

public class CaveBallContent : IContent
{
    private CaveBallDialog _dialog;
    private CaveBallSetting _settings;
    private GameObject _BGInstance;
    private CaveBallGameManager _gameManager;
    private CaveBallDisplayRig _displayRig;

    protected override void _OnLoadStart()
    {
        _BGInstance = AddressableLoader.Instance.Instantiate("CaveballBG", transform);
        if (_BGInstance != null)
        {
            _BGInstance.SetActive(false);
        }
        else
        {
            Debug.LogError("[CaveBallContent] CaveballBG Addressable 생성에 실패했습니다.");
        }

        _SetLoadComplete();
    }

    protected override void _OnLoadComplete()
    {
        const string settingsPath = "Setting/CaveballSetting.json";
        _settings = _LoadSettings<CaveBallSetting>(settingsPath);

        if (_BGInstance == null)
        {
            return;
        }

        _displayRig = _BGInstance.GetComponent<CaveBallDisplayRig>();
        if (_displayRig == null)
        {
            _displayRig = _BGInstance.AddComponent<CaveBallDisplayRig>();
        }
        _displayRig.Configure(_settings);

        _gameManager = _BGInstance.GetComponent<CaveBallGameManager>();
        if (_gameManager == null)
        {
            _gameManager = _BGInstance.AddComponent<CaveBallGameManager>();
        }
        _gameManager.Initialize(_settings, _displayRig);
    }

    protected override void _OnUILoadComplete()
    {
        _dialog = _GetDialog<CaveBallDialog>(DialogName.CaveballDialog);
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
