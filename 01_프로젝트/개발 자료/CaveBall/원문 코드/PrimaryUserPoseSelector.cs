using CellBig.Module.RTPoseSeg;
using UnityEngine;

public sealed class PrimaryUserPoseSelector
{
    private int _selectedId = int.MinValue;

    public TrackedPersonPose Select(PoseFrame frame)
    {
        if (frame?.people == null || frame.people.Count == 0)
        {
            return null;
        }

        TrackedPersonPose best = null;
        float bestScore = float.NegativeInfinity;
        Vector2 frameCenter = new Vector2(frame.resolution.x * 0.5f, frame.resolution.y * 0.5f);
        float diagonal = Mathf.Max(1f, frame.resolution.magnitude);

        foreach (TrackedPersonPose person in frame.people)
        {
            if (person == null)
            {
                continue;
            }

            float area = Mathf.Max(0f, person.bbox.width * person.bbox.height);
            float normalizedArea = frame.resolution.x > 0 && frame.resolution.y > 0
                ? area / (frame.resolution.x * frame.resolution.y)
                : area;
            float centerPenalty = frame.resolution.x > 0 && frame.resolution.y > 0
                ? Vector2.Distance(person.bbox.center, frameCenter) / diagonal
                : 0f;
            float stickyBonus = person.tempId == _selectedId ? 2f : 0f;
            float score = stickyBonus + normalizedArea * 3f + person.score - centerPenalty;

            if (score > bestScore)
            {
                best = person;
                bestScore = score;
            }
        }

        if (best != null)
        {
            _selectedId = best.tempId;
        }

        return best;
    }

    public void Reset()
    {
        _selectedId = int.MinValue;
    }
}
