namespace CellBig.Constants
{
    public enum LocalizingType
    {
        KR,
        JP,
        EN,
        CH,
    }

    public enum ModuleName
    {
        None,
        BaseCamera = 1,
        VideoDevice = 9,
        OSCReceiver = 17,
        RTPoseSeg = 20,

    }

    public enum SceneName
    {
        None,
        CaveballScene,
        CaveActionScene

    }

    public enum ContentName
    {
        None,
        CaveballContent,
        CaveActionContent,
    }

    public enum DialogName
    {
        None,
        CaveballDialog,
        CaveActionDialog,
        GlobalDialog = 1000,
    }
}
