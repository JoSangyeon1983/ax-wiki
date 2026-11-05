using UnityEngine;

public enum CaveBallState
{
    White,
    Yellow,
    Red,
    Blue
}

public enum CaveBallBrickColor
{
    Red,
    Blue
}

public static class CaveBallRules
{
    public static bool CanApplyHandColor(CaveBallState current, CaveBallState requested)
    {
        return current == CaveBallState.White &&
               (requested == CaveBallState.Red || requested == CaveBallState.Blue);
    }

    public static bool CanBreakBrick(CaveBallBrickColor brickColor, CaveBallState ballState)
    {
        return (brickColor == CaveBallBrickColor.Red && ballState == CaveBallState.Red) ||
               (brickColor == CaveBallBrickColor.Blue && ballState == CaveBallState.Blue);
    }

    public static Vector2 NormalizePoint(
        Vector2 raw,
        Vector2 minimum,
        Vector2 maximum,
        bool invertX,
        bool invertY)
    {
        float xRange = Mathf.Max(0.0001f, maximum.x - minimum.x);
        float yRange = Mathf.Max(0.0001f, maximum.y - minimum.y);
        float x = Mathf.Clamp01((raw.x - minimum.x) / xRange);
        float y = Mathf.Clamp01((raw.y - minimum.y) / yRange);

        if (invertX) x = 1f - x;
        if (invertY) y = 1f - y;
        return new Vector2(x, y);
    }

    public static Vector2 QuantizeDirection8(Vector2 direction)
    {
        if (direction.sqrMagnitude < 0.0001f)
        {
            return Vector2.zero;
        }

        float angle = Mathf.Atan2(direction.y, direction.x) * Mathf.Rad2Deg;
        float snappedAngle = Mathf.Round(angle / 45f) * 45f * Mathf.Deg2Rad;
        return new Vector2(Mathf.Cos(snappedAngle), Mathf.Sin(snappedAngle)).normalized;
    }

    public static Vector3 FloorNormalizedToWorld(
        Vector2 normalized,
        Vector3 arenaCenter,
        Vector3 arenaSize)
    {
        Vector3 minimum = arenaCenter - arenaSize * 0.5f;
        return new Vector3(
            Mathf.Lerp(minimum.x, minimum.x + arenaSize.x, normalized.x),
            arenaCenter.y,
            Mathf.Lerp(minimum.z, minimum.z + arenaSize.z, normalized.y));
    }

    public static Vector2 WorldToFloorNormalized(
        Vector3 world,
        Vector3 arenaCenter,
        Vector3 arenaSize)
    {
        Vector3 minimum = arenaCenter - arenaSize * 0.5f;
        return new Vector2(
            Mathf.InverseLerp(minimum.x, minimum.x + arenaSize.x, world.x),
            Mathf.InverseLerp(minimum.z, minimum.z + arenaSize.z, world.z));
    }
}
