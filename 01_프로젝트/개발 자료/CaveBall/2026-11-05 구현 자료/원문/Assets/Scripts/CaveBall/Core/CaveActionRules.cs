using System.Collections.Generic;
using UnityEngine;

public static class CaveActionRules
{
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

    public static Rect CalculatePlatformRect(
        IReadOnlyList<Vector2> points,
        bool leftPlayer,
        Vector2 minimumSize,
        Vector2 maximumSize,
        Vector2 pointPadding)
    {
        if (points == null || points.Count == 0)
        {
            return default;
        }

        Vector2 sum = Vector2.zero;
        Vector2 minimum = new(float.PositiveInfinity, float.PositiveInfinity);
        Vector2 maximum = new(float.NegativeInfinity, float.NegativeInfinity);
        for (int i = 0; i < points.Count; i++)
        {
            Vector2 point = points[i];
            sum += point;
            minimum = Vector2.Min(minimum, point);
            maximum = Vector2.Max(maximum, point);
        }

        Vector2 center = sum / points.Count;
        Vector2 size = maximum - minimum + pointPadding * 2f;
        size.x = Mathf.Clamp(size.x, minimumSize.x, maximumSize.x);
        size.y = Mathf.Clamp(size.y, minimumSize.y, maximumSize.y);

        float halfMinimum = leftPlayer ? 0f : 0.5f;
        float halfMaximum = leftPlayer ? 0.5f : 1f;
        center.x = Mathf.Clamp(center.x, halfMinimum + size.x * 0.5f, halfMaximum - size.x * 0.5f);
        center.y = Mathf.Clamp(center.y, size.y * 0.5f, 1f - size.y * 0.5f);
        return new Rect(center - size * 0.5f, size);
    }

    public static Rect CalculateFixedPlatformRect(
        IReadOnlyList<Vector2> points,
        bool leftPlayer,
        Vector2 fixedSize)
    {
        return CalculateFixedPlatformRect(
            points,
            leftPlayer,
            fixedSize,
            new List<float>(),
            new List<float>());
    }

    public static Rect CalculateFixedPlatformRect(
        IReadOnlyList<Vector2> points,
        bool leftPlayer,
        Vector2 fixedSize,
        List<float> xBuffer,
        List<float> yBuffer)
    {
        if (points == null || points.Count == 0)
        {
            return default;
        }

        xBuffer.Clear();
        yBuffer.Clear();
        for (int i = 0; i < points.Count; i++)
        {
            xBuffer.Add(points[i].x);
            yBuffer.Add(points[i].y);
        }
        xBuffer.Sort();
        yBuffer.Sort();

        Vector2 center = new(
            Median(xBuffer),
            Median(yBuffer));
        Vector2 size = new(
            Mathf.Clamp(fixedSize.x, 0.001f, 0.5f),
            Mathf.Clamp(fixedSize.y, 0.001f, 1f));

        float halfMinimum = leftPlayer ? 0f : 0.5f;
        float halfMaximum = leftPlayer ? 0.5f : 1f;
        center.x = Mathf.Clamp(center.x, halfMinimum + size.x * 0.5f, halfMaximum - size.x * 0.5f);
        center.y = Mathf.Clamp(center.y, size.y * 0.5f, 1f - size.y * 0.5f);
        return new Rect(center - size * 0.5f, size);
    }

    public static Rect MirrorHorizontally(Rect source)
    {
        Vector2 center = source.center;
        center.x = 1f - center.x;
        return new Rect(center - source.size * 0.5f, source.size);
    }

    private static float Median(IReadOnlyList<float> sortedValues)
    {
        int middle = sortedValues.Count / 2;
        return sortedValues.Count % 2 == 0
            ? (sortedValues[middle - 1] + sortedValues[middle]) * 0.5f
            : sortedValues[middle];
    }
}
