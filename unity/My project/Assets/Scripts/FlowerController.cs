using UnityEngine;

/// Drives the flower visual from the emotion server's valence signal.
/// bloomAmount accumulates slowly from valence rather than snapping, so the
/// flower reads as gradually growing/wilting instead of twitching.
///
/// The imported model is a single combined mesh (pot + plant as one piece,
/// no separate stem bone), so "wilting" is approximated with a whole-object
/// tilt plus a color shift toward brown, rather than bending an isolated stem.
public class FlowerController : MonoBehaviour
{
    [Tooltip("How fast bloomAmount accumulates per second from CurrentValence.")]
    public float growthRate = 1f;

    [Range(0f, 1f)]
    public float bloomAmount = 0.5f;

    [Tooltip("Scale multiplier applied on top of this object's starting scale.")]
    public float wiltedScaleMultiplier = 0.85f;
    public float bloomedScaleMultiplier = 1.1f;

    [Tooltip("Extra forward tilt (degrees) applied at full wilt, on top of the starting rotation. " +
             "The imported model fuses the pot and plant into one rigid mesh, so any nonzero value here tips the whole pot over, not just the plant — leave at 0 unless the model is split into separate pot/plant parts.")]
    public float wiltedTiltDegrees = 0f;

    public Color bloomedTint = Color.white;
    public Color wiltedTint = new Color(0.5f, 0.35f, 0.2f); // desaturated brown

    private Vector3 _baseScale;
    private Quaternion _baseRotation;
    private Renderer _renderer;
    private static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");

    private void Awake()
    {
        _baseScale = transform.localScale;
        _baseRotation = transform.localRotation;
        _renderer = GetComponentInChildren<Renderer>();
    }

    private void Update()
    {
        if (EmotionState.Instance != null)
        {
            bloomAmount += EmotionState.Instance.CurrentValence * growthRate * Time.deltaTime;
            bloomAmount = Mathf.Clamp01(bloomAmount);
        }

        float scaleMultiplier = Mathf.Lerp(wiltedScaleMultiplier, bloomedScaleMultiplier, bloomAmount);
        transform.localScale = _baseScale * scaleMultiplier;

        float tilt = Mathf.Lerp(wiltedTiltDegrees, 0f, bloomAmount);
        transform.localRotation = _baseRotation * Quaternion.Euler(tilt, 0f, 0f);

        if (_renderer != null)
        {
            Color tint = Color.Lerp(wiltedTint, bloomedTint, bloomAmount);
            _renderer.material.SetColor(BaseColorId, tint);
        }
    }
}
