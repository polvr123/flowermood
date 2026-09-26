using UnityEngine;

/// Singleton exposing the emotion server's signals to the rest of the scene.
/// Reads the latest buffered UDP packet once per frame and lerps toward it,
/// holding last-known values if the server goes quiet instead of resetting.
[RequireComponent(typeof(UdpReceiver))]
public class EmotionState : MonoBehaviour
{
    public static EmotionState Instance { get; private set; }

    [Tooltip("How quickly CurrentValence/CurrentCalm chase the incoming raw values, per second.")]
    public float lerpSpeed = 2f;

    [Tooltip("Seconds without a packet before IsConnected drops to false.")]
    public float connectionTimeout = 2f;

    [Tooltip("Log each received packet to the Console (Phase 1 build-order step 3 verification).")]
    public bool logPackets = false;

    public float CurrentValence { get; private set; }
    public float CurrentCalm { get; private set; }
    public bool IsConnected { get; private set; }

    private UdpReceiver _receiver;
    private float _rawValence;
    private float _rawCalm;
    private float _lastPacketRealtime = -Mathf.Infinity;

    [System.Serializable]
    private class Packet
    {
        public float valence;
        public float calm;
        public bool face_detected;
        public double timestamp;
    }

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
        _receiver = GetComponent<UdpReceiver>();
    }

    private void Update()
    {
        string json = _receiver.TakeLatestJson();
        if (json != null)
        {
            Packet packet = JsonUtility.FromJson<Packet>(json);
            if (packet != null)
            {
                _lastPacketRealtime = Time.realtimeSinceStartup;
                // Per spec: while no face is detected the server already holds its
                // last smoothed values, so we always adopt the incoming numbers.
                _rawValence = packet.valence;
                _rawCalm = packet.calm;
                if (logPackets)
                {
                    Debug.Log($"valence={packet.valence:+0.00;-0.00} calm={packet.calm:0.00} face_detected={packet.face_detected}");
                }
            }
        }

        IsConnected = Time.realtimeSinceStartup - _lastPacketRealtime <= connectionTimeout;

        float t = 1f - Mathf.Exp(-lerpSpeed * Time.deltaTime);
        CurrentValence = Mathf.Lerp(CurrentValence, _rawValence, t);
        CurrentCalm = Mathf.Lerp(CurrentCalm, _rawCalm, t);
    }
}
