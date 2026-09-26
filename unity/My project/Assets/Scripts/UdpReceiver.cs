using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

/// Listens for emotion-server JSON packets on a background thread and exposes
/// only the latest one. All socket work stays off the main thread; Unity APIs
/// are never touched from here.
public class UdpReceiver : MonoBehaviour
{
    public int port = 5555;

    private UdpClient _client;
    private Thread _listenThread;
    private volatile bool _running;

    private readonly object _lock = new object();
    private string _latestJson;
    private bool _hasNewPacket;

    private void Awake()
    {
        _client = new UdpClient(port);
        _running = true;
        _listenThread = new Thread(ListenLoop) { IsBackground = true };
        _listenThread.Start();
    }

    private void ListenLoop()
    {
        var remoteEndPoint = new IPEndPoint(IPAddress.Any, port);
        while (_running)
        {
            try
            {
                byte[] data = _client.Receive(ref remoteEndPoint);
                string json = Encoding.UTF8.GetString(data);
                lock (_lock)
                {
                    _latestJson = json;
                    _hasNewPacket = true;
                }
            }
            catch (SocketException)
            {
                // Client was closed (OnDestroy) or a transient network error; loop exits via _running.
            }
        }
    }

    /// Returns the latest packet's JSON and clears the pending flag, or null if nothing new arrived.
    public string TakeLatestJson()
    {
        lock (_lock)
        {
            if (!_hasNewPacket) return null;
            _hasNewPacket = false;
            return _latestJson;
        }
    }

    private void OnDestroy()
    {
        _running = false;
        _client?.Close();
        _listenThread?.Join(200);
    }
}
