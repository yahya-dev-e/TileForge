using UnityEngine;

namespace TileForge.Client
{
    /// <summary>
    /// Smoothly moves a 2D Point Light across the scene to showcase dynamic normal map relief.
    /// Supports both interactive mouse cursor tracking and automated demo oscillation.
    /// </summary>
    public class LightFollower : MonoBehaviour
    {
        public enum FollowMode
        {
            FollowMouse,
            AutoOscillateDemo,
            Both
        }

        [Header("Tracking Mode")]
        [SerializeField] private FollowMode mode = FollowMode.Both;

        [Header("Motion Smoothing")]
        [Tooltip("Higher values produce faster, tighter tracking.")]
        [SerializeField] private float smoothSpeed = 12f;
        [SerializeField] private float lightZOffset = -1.5f;

        [Header("Automated Demo Orbit (When Mouse is Idle)")]
        [SerializeField] private bool autoOrbitWhenIdle = true;
        [SerializeField] private float idleThresholdSeconds = 1.5f;
        [SerializeField] private float orbitRadiusX = 3.5f;
        [SerializeField] private float orbitRadiusY = 1.8f;
        [SerializeField] private float orbitSpeed = 1.2f;

        private Camera mainCamera;
        private Vector3 targetPosition;
        private Vector3 lastMouseScreenPos;
        private float mouseIdleTimer;
        private Vector3 orbitCenter;

        private void Start()
        {
            mainCamera = Camera.main;
            targetPosition = transform.position;
            orbitCenter = transform.position;
            lastMouseScreenPos = Input.mousePosition;
        }

        private void Update()
        {
            if (mainCamera == null)
            {
                mainCamera = Camera.main;
                if (mainCamera == null) return;
            }

            Vector3 currentMousePos = Input.mousePosition;
            bool mouseMoved = (currentMousePos - lastMouseScreenPos).sqrMagnitude > 4f;

            if (mouseMoved)
            {
                mouseIdleTimer = 0f;
                lastMouseScreenPos = currentMousePos;
            }
            else
            {
                mouseIdleTimer += Time.deltaTime;
            }

            bool shouldUseOrbit = mode == FollowMode.AutoOscillateDemo ||
                                  (mode == FollowMode.Both && autoOrbitWhenIdle && mouseIdleTimer > idleThresholdSeconds);

            if (shouldUseOrbit)
            {
                // Smooth sinusoidal sweeping orbit across the tiles
                float t = Time.time * orbitSpeed;
                float ox = Mathf.Sin(t) * orbitRadiusX;
                float oy = Mathf.Cos(t * 1.3f) * orbitRadiusY;
                targetPosition = new Vector3(orbitCenter.x + ox, orbitCenter.y + oy, lightZOffset);
            }
            else
            {
                // Convert mouse position to world coordinates
                Vector3 screenPos = Input.mousePosition;
                screenPos.z = -mainCamera.transform.position.z + lightZOffset;
                Vector3 worldPos = mainCamera.ScreenToWorldPoint(screenPos);
                worldPos.z = lightZOffset;
                targetPosition = worldPos;
            }

            // Smooth interpolation to prevent jittering
            transform.position = Vector3.Lerp(transform.position, targetPosition, smoothSpeed * Time.deltaTime);
        }

        private void OnDrawGizmosSelected()
        {
            Gizmos.color = new Color(1f, 0.9f, 0.2f, 0.4f);
            Gizmos.DrawWireSphere(transform.position, 0.4f);
            if (autoOrbitWhenIdle)
            {
                Gizmos.color = new Color(0.2f, 0.8f, 1f, 0.25f);
                Gizmos.DrawWireCube(orbitCenter, new Vector3(orbitRadiusX * 2f, orbitRadiusY * 2f, 0.1f));
            }
        }
    }
}
