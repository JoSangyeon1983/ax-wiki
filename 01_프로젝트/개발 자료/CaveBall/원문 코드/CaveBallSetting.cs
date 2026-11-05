using UnityEngine;
using CellBig;

[System.Serializable]
public class CaveBallSetting : SettingBase
{
    public bool DebugMode = false;

    [Header("Display")]
    public int LeftDisplay = 0;
    public int FrontDisplay = 1;
    public int RightDisplay = 2;
    public int FloorDisplay = 3;
    public int[] FloorBlendDisplays = { 4, 5 };

    [Header("Arena")]
    public Vector3 ArenaCenter = new Vector3(0f, 9.75f, 0f);
    public Vector3 ArenaSize = new Vector3(20f, 10f, 20f);
    public float FrontInteractionDepth = 10f;

    [Header("Ball")]
    public float BallSpeed = 8f;
    public float FloorBounceAcceleration = 1.2f;
    public float MaximumBallSpeed = 18f;
    public float MinimumAxisSpeed = 1.25f;
    public float HandColorDuration = 5f;
    public float RoundResetDelay = 3f;
    public int BrickBreakPoolSize = 6;
    public float BrickBreakEffectDuration = 2f;

    [Header("Hand Tracking")]
    public bool MirrorPoseX = false;
    public bool InvertPoseY = false;
    public int MaxTrackedPeople = 4;
    [Range(0f, 1f)] public float MinimumWristConfidence = 0.35f;
    [Range(0f, 0.5f)] public float HandContactViewportRadius = 0.1f;
    public float PoseTimeout = 0.5f;

    [Header("Floor OSC Calibration")]
    public int FloorSensorId = 0;
    public Vector2 OscMinimum = Vector2.zero;
    public Vector2 OscMaximum = Vector2.one;
    public bool InvertOscX = false;
    public bool InvertOscY = true;
    [Range(0f, 0.5f)] public float FloorTouchViewportRadius = 0.1f;
    public float FloorHeightTolerance = 2f;
    public float FloorContactHoldDuration = 0.1f;
    public float FloorTouchMergeDistance = 0.08f;
    public float FloorBounceCooldown = 0.2f;

    [Header("Camera Shake")]
    public float BrickCameraShakeDuration = 0.2f;
    public float BrickCameraShakePosition = 0.12f;
    public float BrickCameraShakeRotation = 1.5f;

    [Header("Scoreboard")]
    public float ScoreboardFontSize = 110f;
    public float ScoreboardTopOffset = 80f;
    public Color RedScoreColor = new Color(1f, 0.12f, 0.08f, 1f);
    public Color BlueScoreColor = new Color(0.05f, 0.4f, 1f, 1f);
    public float ScoreShakeDuration = 0.28f;
    public float ScoreShakeStrength = 35f;
    public float ScorePunchScale = 0.25f;
}