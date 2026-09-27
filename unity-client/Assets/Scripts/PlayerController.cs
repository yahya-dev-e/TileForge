using UnityEngine;

namespace TileForge.Client
{
    /// <summary>
    /// Lightweight 2D Platformer Character Controller for testing generated TileForge tiles and colliders.
    /// </summary>
    [RequireComponent(typeof(Rigidbody2D))]
    [RequireComponent(typeof(Collider2D))]
    public class PlayerController : MonoBehaviour
    {
        [Header("Movement Parameters")]
        [Tooltip("Horizontal traversal speed.")]
        [SerializeField] private float moveSpeed = 6.5f;

        [Tooltip("Instant vertical impulse applied upon jumping.")]
        [SerializeField] private float jumpForce = 12f;

        [Tooltip("Gravity multiplier applied when falling for snappier jumping.")]
        [SerializeField] private float fallMultiplier = 2.5f;

        [Header("Ground Detection")]
        [SerializeField] private Transform groundCheck;
        [SerializeField] private float groundCheckRadius = 0.22f;
        [SerializeField] private LayerMask groundLayer;

        [Header("Visuals")]
        [SerializeField] private SpriteRenderer spriteRenderer;

        private Rigidbody2D rb;
        private float horizontalInput;
        private bool isGrounded;
        private bool jumpRequested;

        private void Awake()
        {
            rb = GetComponent<Rigidbody2D>();
            if (spriteRenderer == null)
            {
                spriteRenderer = GetComponentInChildren<SpriteRenderer>();
            }

            // Ensure groundCheck transform exists
            if (groundCheck == null)
            {
                GameObject checkObj = new GameObject("GroundCheck");
                checkObj.transform.SetParent(transform);
                checkObj.transform.localPosition = new Vector3(0f, -0.55f, 0f);
                groundCheck = checkObj.transform;
            }
        }

        private void Update()
        {
            // Gather input in Update for frame-accurate responsiveness
            horizontalInput = Input.GetAxisRaw("Horizontal");

            if ((Input.GetButtonDown("Jump") || Input.GetKeyDown(KeyCode.Space) || Input.GetKeyDown(KeyCode.W) || Input.GetKeyDown(KeyCode.UpArrow)) && isGrounded)
            {
                jumpRequested = true;
            }

            // Flip sprite based on direction
            if (spriteRenderer != null)
            {
                if (horizontalInput > 0.05f)
                    spriteRenderer.flipX = false;
                else if (horizontalInput < -0.05f)
                    spriteRenderer.flipX = true;
            }
        }

        private void FixedUpdate()
        {
            // Evaluate ground check
            if (groundLayer.value == 0)
            {
                // Default to checking everything except Player layer
                isGrounded = Physics2D.OverlapCircle(groundCheck.position, groundCheckRadius, ~LayerMask.GetMask("Player", "Ignore Raycast"));
            }
            else
            {
                isGrounded = Physics2D.OverlapCircle(groundCheck.position, groundCheckRadius, groundLayer);
            }

            // Horizontal velocity
            rb.velocity = new Vector2(horizontalInput * moveSpeed, rb.velocity.y);

            // Execute jump
            if (jumpRequested)
            {
                rb.velocity = new Vector2(rb.velocity.x, jumpForce);
                jumpRequested = false;
            }

            // Snappy falling physics
            if (rb.velocity.y < 0)
            {
                rb.velocity += Vector2.up * Physics2D.gravity.y * (fallMultiplier - 1f) * Time.fixedDeltaTime;
            }
        }

        private void OnDrawGizmosSelected()
        {
            if (groundCheck != null)
            {
                Gizmos.color = isGrounded ? Color.green : Color.red;
                Gizmos.DrawWireSphere(groundCheck.position, groundCheckRadius);
            }
        }
    }
}
