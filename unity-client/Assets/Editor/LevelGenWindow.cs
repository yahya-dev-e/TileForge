using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEngine.Networking;

namespace TileForge.Editor
{
    /// <summary>
    /// TileForge AI - In-Engine 2D Generative Level Design & Normal Map Baker Window.
    /// Communicates with local or cloud FastAPI / SD-Turbo backend over asynchronous HTTP.
    /// </summary>
    public class LevelGenWindow : EditorWindow
    {
        private const string DEFAULT_SERVER_URL = "http://54.159.8.64:9000";
        private const string GENERATED_FOLDER = "Assets/Generated";

        [Serializable]
        public class Point2DData
        {
            public float x;
            public float y;
        }

        [Serializable]
        public class PolygonListWrapper
        {
            // JsonUtility cannot deserialize nested collections (e.g. List<List<T>>),
            // so each polygon is wrapped in its own named "points" field instead.
            public List<Point2DData> points;
        }

        [Serializable]
        public class TileRequestPayload
        {
            public string prompt;
            public string negative_prompt;
            public int width = 512;
            public int height = 512;
            public int steps = 2;
            public float guidance_scale = 1.5f;
            public int seed = -1;
            public bool seamless = true;
            public float seamless_blend_ratio = 0.15f;
            public bool generate_normal_map = true;
            public float normal_strength = 2.5f;
            public bool invert_normal_y = false;
            public bool generate_collider = true;
            public float collider_tolerance = 2.0f;
        }

        [Serializable]
        public class TileResponsePayload
        {
            public string status;
            public int seed;
            public float generation_time_ms;
            public string color_map_base64;
            public string normal_map_base64;
            public List<PolygonListWrapper> collider_polygons;
        }

        [Serializable]
        public class HealthResponsePayload
        {
            public string status;
            public string version;
            public string device;
            public string gpu_name;
            public bool model_loaded;
        }

        // GUI State & Parameters
        // [SerializeField] is required on every field below so Unity persists it across
        // domain reloads (any script recompile) - without it, EditorWindow fields silently
        // reset to their initializer default, which made serverUrl/apiKey revert to
        // 127.0.0.1 with no visible cause.
        [SerializeField] private string serverUrl = DEFAULT_SERVER_URL;
        [SerializeField] private string apiKey = "";
        [SerializeField] private string assetPrefix = "DungeonTile_01";
        [SerializeField] private string prompt = "weathered ancient dungeon cobblestone wall, grey mossy stones, dark mortar, flat 2d game texture, seamless platformer tile, top-down orthographic";
        [SerializeField] private string negativePrompt = "blurry, 3d perspective, isometric, shadows, vignette, watermarks, character, noisy";

        [SerializeField] private int selectedPresetIndex = 0;
        private readonly string[] presetNames = new string[]
        {
            "Ancient Dungeon Cobblestone",
            "Volcanic Obsidian & Lava Veins",
            "Cyberpunk Neon Circuitry",
            "Enchanted Forest Wood Planks",
            "Amethyst Crystal Cavern",
            "Steampunk Rusted Brass Tiles"
        };

        [SerializeField] private int steps = 2;
        [SerializeField] private float guidanceScale = 1.5f;
        [SerializeField] private int seed = -1;
        [SerializeField] private bool randomizeSeed = true;
        [SerializeField] private bool seamless = true;
        [SerializeField] private bool generateNormal = true;
        [SerializeField] private float normalStrength = 2.5f;
        [SerializeField] private bool generateCollider = true;
        [SerializeField] private float colliderTolerance = 2.0f;

        // Runtime Async State
        private bool isRequestActive = false;
        private string connectionStatusText = "Not Connected";
        private Color connectionStatusColor = Color.gray;
        private string statusMessage = "Ready. Configure prompt and generate.";
        private Texture2D previewDiffuseTexture;
        private Texture2D previewNormalTexture;
        private TileResponsePayload lastResponse;
        private Vector2 scrollPos;

        [MenuItem("Window/TileForge/Level Generator", false, 2050)]
        public static void ShowWindow()
        {
            LevelGenWindow window = GetWindow<LevelGenWindow>("TileForge AI");
            window.minSize = new Vector2(450, 680);
            window.Show();
        }

        private void OnEnable()
        {
            // Auto test connection on window open
            TestBackendConnection();
        }

        private void OnGUI()
        {
            scrollPos = EditorGUILayout.BeginScrollView(scrollPos);

            DrawHeader();
            DrawServerSection();
            EditorGUILayout.Space(6);
            DrawPresetSection();
            EditorGUILayout.Space(6);
            DrawPromptParameters();
            EditorGUILayout.Space(6);
            DrawProcessingToggles();
            EditorGUILayout.Space(8);
            DrawActionButtons();
            EditorGUILayout.Space(8);
            DrawLivePreviews();

            EditorGUILayout.EndScrollView();
        }

        private void DrawHeader()
        {
            EditorGUILayout.BeginVertical(EditorStyles.helpBox);
            GUILayout.Space(4);
            GUIStyle titleStyle = new GUIStyle(EditorStyles.boldLabel)
            {
                fontSize = 15,
                alignment = TextAnchor.MiddleCenter
            };
            GUILayout.Label("🛠️ TileForge AI: Real-Time 2D Level Generator", titleStyle);
            GUIStyle subStyle = new GUIStyle(EditorStyles.miniLabel)
            {
                alignment = TextAnchor.MiddleCenter
            };
            GUILayout.Label("Sub-second diffusion, seamless wrapping & tangent normal baker for URP 2D", subStyle);
            GUILayout.Space(4);
            EditorGUILayout.EndVertical();
        }

        private void DrawServerSection()
        {
            EditorGUILayout.LabelField("Backend Connection", EditorStyles.boldLabel);
            EditorGUILayout.BeginHorizontal();
            serverUrl = EditorGUILayout.TextField("Server URL", serverUrl);
            if (GUILayout.Button("Test Connection", GUILayout.Width(120)))
            {
                TestBackendConnection();
            }
            EditorGUILayout.EndHorizontal();

            apiKey = EditorGUILayout.PasswordField("API Key (if server requires one)", apiKey);

            EditorGUILayout.BeginHorizontal();
            GUIStyle statusDotStyle = new GUIStyle(EditorStyles.label);
            statusDotStyle.normal.textColor = connectionStatusColor;
            GUILayout.Label("● Status: " + connectionStatusText, statusDotStyle);
            EditorGUILayout.EndHorizontal();
        }

        private void DrawPresetSection()
        {
            EditorGUILayout.LabelField("Prompt Presets", EditorStyles.boldLabel);
            int newPreset = EditorGUILayout.Popup("Curated Template", selectedPresetIndex, presetNames);
            if (newPreset != selectedPresetIndex)
            {
                selectedPresetIndex = newPreset;
                ApplySelectedPreset();
            }
        }

        private void ApplySelectedPreset()
        {
            switch (selectedPresetIndex)
            {
                case 0: // Dungeon
                    prompt = "weathered ancient dungeon cobblestone wall, grey mossy stones, dark mortar, flat 2d game texture, seamless platformer tile, top-down orthographic";
                    normalStrength = 2.8f;
                    steps = 2;
                    assetPrefix = "DungeonStone_01";
                    break;
                case 1: // Volcanic
                    prompt = "cracked volcanic obsidian rock tile, glowing molten orange magma veins, jagged basalt stones, flat 2d game texture, seamless texture";
                    normalStrength = 3.2f;
                    steps = 2;
                    assetPrefix = "VolcanicLava_01";
                    break;
                case 2: // Cyberpunk
                    prompt = "futuristic sci-fi spaceship hull panel, dark brushed steel metal plates, glowing cyan neon circuitry lines, hexagonal rivets, clean hard-surface 2d game texture";
                    normalStrength = 2.2f;
                    steps = 2;
                    assetPrefix = "CyberCircuit_01";
                    break;
                case 3: // Enchanted wood
                    prompt = "weathered aged dark oak wood planks, ancient elven golden glowing runes carved into timber, leafy vines creeping, flat 2d texture, seamless fantasy tile";
                    normalStrength = 2.5f;
                    steps = 2;
                    assetPrefix = "EnchantedWood_01";
                    break;
                case 4: // Crystal
                    prompt = "dark underground cave bedrock embedded with vibrant purple amethyst crystal cluster facets, crystalline geode, flat orthographic 2d game texture, seamless";
                    normalStrength = 3.0f;
                    steps = 3;
                    assetPrefix = "AmethystCrystal_01";
                    break;
                case 5: // Steampunk
                    prompt = "steampunk industrial brass and copper metal tiles, heavy bolts, rusted metal edges, steam vents, flat 2d platformer texture, seamless repeating pattern";
                    normalStrength = 2.6f;
                    steps = 2;
                    assetPrefix = "SteampunkBrass_01";
                    break;
            }
            Repaint();
        }

        private void DrawPromptParameters()
        {
            EditorGUILayout.LabelField("Generation Settings", EditorStyles.boldLabel);
            assetPrefix = EditorGUILayout.TextField("Asset Output Name", assetPrefix);

            EditorGUILayout.LabelField("Prompt:");
            prompt = EditorGUILayout.TextArea(prompt, GUILayout.Height(45));

            EditorGUILayout.LabelField("Negative Prompt:");
            negativePrompt = EditorGUILayout.TextArea(negativePrompt, GUILayout.Height(30));

            steps = EditorGUILayout.IntSlider("Inference Steps (Turbo)", steps, 1, 6);
            guidanceScale = EditorGUILayout.Slider("Guidance Scale", guidanceScale, 0.0f, 4.0f);

            EditorGUILayout.BeginHorizontal();
            randomizeSeed = EditorGUILayout.Toggle("Randomize Seed", randomizeSeed);
            if (!randomizeSeed)
            {
                seed = EditorGUILayout.IntField("Fixed Seed", seed);
            }
            EditorGUILayout.EndHorizontal();
        }

        private void DrawProcessingToggles()
        {
            EditorGUILayout.LabelField("Post-Processing Pipeline", EditorStyles.boldLabel);
            seamless = EditorGUILayout.Toggle("Seamless Border Wrap", seamless);

            generateNormal = EditorGUILayout.Toggle("Bake Tangent Normal Map", generateNormal);
            if (generateNormal)
            {
                normalStrength = EditorGUILayout.Slider("  Normal Relief Strength", normalStrength, 0.5f, 6.0f);
            }

            generateCollider = EditorGUILayout.Toggle("Extract 2D Polygon Collider", generateCollider);
            if (generateCollider)
            {
                colliderTolerance = EditorGUILayout.Slider("  RDP Collider Tolerance", colliderTolerance, 0.5f, 5.0f);
            }
        }

        private void DrawActionButtons()
        {
            GUI.enabled = !isRequestActive;

            GUIStyle actionButtonStyle = new GUIStyle(GUI.skin.button)
            {
                fontStyle = FontStyle.Bold,
                fontSize = 13,
                fixedHeight = 36
            };

            if (GUILayout.Button(isRequestActive ? "⏳ Generating via SD-Turbo..." : "⚡ Generate Tile & Shaders", actionButtonStyle))
            {
                DispatchGenerateRequest();
            }

            GUI.enabled = true;

            EditorGUILayout.HelpBox(statusMessage, MessageType.Info);
        }

        private void DrawLivePreviews()
        {
            if (previewDiffuseTexture == null && previewNormalTexture == null)
                return;

            EditorGUILayout.LabelField("Live Previews", EditorStyles.boldLabel);

            EditorGUILayout.BeginHorizontal();

            if (previewDiffuseTexture != null)
            {
                EditorGUILayout.BeginVertical(EditorStyles.helpBox, GUILayout.Width(200));
                GUILayout.Label("Diffuse Texture (512x512)", EditorStyles.boldLabel);
                Rect r = GUILayoutUtility.GetRect(190, 190);
                GUI.DrawTexture(r, previewDiffuseTexture, ScaleMode.ScaleToFit);
                EditorGUILayout.EndVertical();
            }

            if (previewNormalTexture != null)
            {
                EditorGUILayout.BeginVertical(EditorStyles.helpBox, GUILayout.Width(200));
                GUILayout.Label("Tangent Normal Map", EditorStyles.boldLabel);
                Rect r2 = GUILayoutUtility.GetRect(190, 190);
                GUI.DrawTexture(r2, previewNormalTexture, ScaleMode.ScaleToFit);
                EditorGUILayout.EndVertical();
            }

            EditorGUILayout.EndHorizontal();

            EditorGUILayout.Space(6);

            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("💾 Save Asset Files to Project", GUILayout.Height(30)))
            {
                SaveGeneratedAssetsToProject(spawnInScene: false);
            }

            if (GUILayout.Button("🚀 Save & Spawn in Scene", GUILayout.Height(30)))
            {
                SaveGeneratedAssetsToProject(spawnInScene: true);
            }
            EditorGUILayout.EndHorizontal();
        }

        private void TestBackendConnection()
        {
            string url = serverUrl.TrimEnd('/') + "/health";
            UnityWebRequest req = UnityWebRequest.Get(url);
            req.timeout = 5;
            if (!string.IsNullOrEmpty(apiKey))
            {
                req.SetRequestHeader("X-API-Key", apiKey);
            }

            var op = req.SendWebRequest();
            op.completed += _ =>
            {
                if (req.result == UnityWebRequest.Result.Success)
                {
                    try
                    {
                        var health = JsonUtility.FromJson<HealthResponsePayload>(req.downloadHandler.text);
                        connectionStatusText = $"Connected ({health.device} - {health.gpu_name})";
                        connectionStatusColor = new Color(0.1f, 0.8f, 0.2f);
                        statusMessage = $"Backend Online. Ready for generation on {health.gpu_name}.";
                    }
                    catch
                    {
                        connectionStatusText = "Connected (Online)";
                        connectionStatusColor = Color.green;
                    }
                }
                else
                {
                    connectionStatusText = $"Offline: {req.error}";
                    connectionStatusColor = new Color(0.9f, 0.2f, 0.2f);
                    statusMessage = $"Failed to connect to backend at {url}. Make sure FastAPI is running.";
                }
                req.Dispose();
                Repaint();
            };
        }

        private void DispatchGenerateRequest()
        {
            isRequestActive = true;
            statusMessage = "Dispatching request to SD-Turbo pipeline...";

            TileRequestPayload payload = new TileRequestPayload
            {
                prompt = prompt,
                negative_prompt = negativePrompt,
                width = 512,
                height = 512,
                steps = steps,
                guidance_scale = guidanceScale,
                seed = randomizeSeed ? -1 : seed,
                seamless = seamless,
                generate_normal_map = generateNormal,
                normal_strength = normalStrength,
                generate_collider = generateCollider,
                collider_tolerance = colliderTolerance
            };

            string jsonBody = JsonUtility.ToJson(payload);
            string url = serverUrl.TrimEnd('/') + "/api/v1/generate-tile";

            UnityWebRequest req = new UnityWebRequest(url, "POST");
            byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonBody);
            req.uploadHandler = new UploadHandlerRaw(bodyRaw);
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");
            if (!string.IsNullOrEmpty(apiKey))
            {
                req.SetRequestHeader("X-API-Key", apiKey);
            }
            req.timeout = 45;

            var op = req.SendWebRequest();
            op.completed += _ =>
            {
                isRequestActive = false;
                if (req.result == UnityWebRequest.Result.Success)
                {
                    try
                    {
                        HandleSuccessfulResponse(req.downloadHandler.text);
                    }
                    catch (Exception ex)
                    {
                        statusMessage = "Parse error: " + ex.Message;
                        Debug.LogError("[TileForge] Response deserialization exception: " + ex);
                    }
                }
                else
                {
                    statusMessage = "Error: " + req.error;
                    Debug.LogError("[TileForge] Request failed: " + req.error + " | " + req.downloadHandler.text);
                }
                req.Dispose();
                Repaint();
            };
        }

        private void HandleSuccessfulResponse(string jsonText)
        {
            lastResponse = JsonUtility.FromJson<TileResponsePayload>(jsonText);

            if (!string.IsNullOrEmpty(lastResponse.color_map_base64))
            {
                byte[] diffuseBytes = Convert.FromBase64String(lastResponse.color_map_base64);
                previewDiffuseTexture = new Texture2D(512, 512, TextureFormat.RGBA32, false);
                previewDiffuseTexture.LoadImage(diffuseBytes);
                previewDiffuseTexture.Apply();
            }

            if (!string.IsNullOrEmpty(lastResponse.normal_map_base64))
            {
                byte[] normalBytes = Convert.FromBase64String(lastResponse.normal_map_base64);
                previewNormalTexture = new Texture2D(512, 512, TextureFormat.RGBA32, false);
                previewNormalTexture.LoadImage(normalBytes);
                previewNormalTexture.Apply();
            }

            statusMessage = $"Success! Latency: {lastResponse.generation_time_ms:F1}ms | Seed: {lastResponse.seed}";
            Debug.Log($"[TileForge] Generated tile in {lastResponse.generation_time_ms} ms (Seed: {lastResponse.seed})");
        }

        /// Strips path separators, "..", and other invalid filename characters so
        /// the user-editable Asset Output Name field can't write outside GENERATED_FOLDER.
        private static string SanitizeAssetPrefix(string raw)
        {
            if (string.IsNullOrWhiteSpace(raw))
            {
                return "TileForge_Tile";
            }

            string cleaned = raw.Replace("..", "_");
            foreach (char c in Path.GetInvalidFileNameChars())
            {
                cleaned = cleaned.Replace(c, '_');
            }
            cleaned = cleaned.Replace('/', '_').Replace('\\', '_').Trim();

            return string.IsNullOrEmpty(cleaned) ? "TileForge_Tile" : cleaned;
        }

        /// Uses the first polygon returned by the backend's collider extraction,
        /// falling back to a default unit-square box if none was returned or requested.
        private Vector2[] BuildColliderPoints()
        {
            if (lastResponse?.collider_polygons != null && lastResponse.collider_polygons.Count > 0)
            {
                List<Point2DData> srcPoints = lastResponse.collider_polygons[0].points;
                if (srcPoints != null && srcPoints.Count >= 3)
                {
                    Vector2[] pts = new Vector2[srcPoints.Count];
                    for (int i = 0; i < srcPoints.Count; i++)
                    {
                        pts[i] = new Vector2(srcPoints[i].x, srcPoints[i].y);
                    }
                    return pts;
                }
            }

            return new Vector2[]
            {
                new Vector2(-0.5f, -0.5f),
                new Vector2(0.5f, -0.5f),
                new Vector2(0.5f, 0.5f),
                new Vector2(-0.5f, 0.5f)
            };
        }

        private void SaveGeneratedAssetsToProject(bool spawnInScene)
        {
            if (previewDiffuseTexture == null)
            {
                EditorUtility.DisplayDialog("TileForge", "No generated texture available. Generate first!", "OK");
                return;
            }

            if (!Directory.Exists(GENERATED_FOLDER))
            {
                Directory.CreateDirectory(GENERATED_FOLDER);
            }

            string safePrefix = SanitizeAssetPrefix(assetPrefix);
            string diffusePath = $"{GENERATED_FOLDER}/{safePrefix}_Diffuse.png";
            string normalPath = $"{GENERATED_FOLDER}/{safePrefix}_Normal.png";
            string matPath = $"{GENERATED_FOLDER}/{safePrefix}_Mat.mat";

            // 1. Write diffuse PNG
            byte[] diffusePng = previewDiffuseTexture.EncodeToPNG();
            File.WriteAllBytes(diffusePath, diffusePng);

            // 2. Write normal PNG
            if (previewNormalTexture != null)
            {
                byte[] normalPng = previewNormalTexture.EncodeToPNG();
                File.WriteAllBytes(normalPath, normalPng);
            }

            AssetDatabase.Refresh();

            // 3. Configure Texture Importers
            TextureImporter diffuseImporter = AssetImporter.GetAtPath(diffusePath) as TextureImporter;
            if (diffuseImporter != null)
            {
                diffuseImporter.textureType = TextureImporterType.Sprite;
                diffuseImporter.spriteImportMode = SpriteImportMode.Single;
                diffuseImporter.wrapMode = TextureWrapMode.Repeat;
                diffuseImporter.filterMode = FilterMode.Bilinear;
                diffuseImporter.SaveAndReimport();
            }

            if (previewNormalTexture != null)
            {
                TextureImporter normalImporter = AssetImporter.GetAtPath(normalPath) as TextureImporter;
                if (normalImporter != null)
                {
                    normalImporter.textureType = TextureImporterType.NormalMap;
                    normalImporter.wrapMode = TextureWrapMode.Repeat;
                    normalImporter.filterMode = FilterMode.Bilinear;
                    normalImporter.SaveAndReimport();
                }
            }

            AssetDatabase.Refresh();

            // 4. Create Material with 2D Lit Shader
            Texture2D importedDiffuse = AssetDatabase.LoadAssetAtPath<Texture2D>(diffusePath);
            Texture2D importedNormal = AssetDatabase.LoadAssetAtPath<Texture2D>(normalPath);
            Sprite importedSprite = AssetDatabase.LoadAssetAtPath<Sprite>(diffusePath);

            Shader lit2DShader = Shader.Find("Universal Render Pipeline/2D/Sprite-Lit-Default");
            if (lit2DShader == null) lit2DShader = Shader.Find("Sprites/Default");

            Material mat = new Material(lit2DShader);
            if (importedDiffuse != null) mat.mainTexture = importedDiffuse;
            if (importedNormal != null && mat.HasProperty("_BumpMap"))
            {
                mat.SetTexture("_BumpMap", importedNormal);
            }

            AssetDatabase.CreateAsset(mat, matPath);
            AssetDatabase.SaveAssets();

            // 5. Spawn in Scene if requested
            if (spawnInScene && importedSprite != null)
            {
                GameObject platformObj = new GameObject(safePrefix);
                var sr = platformObj.AddComponent<SpriteRenderer>();
                sr.sprite = importedSprite;
                sr.material = mat;

                var poly = platformObj.AddComponent<PolygonCollider2D>();
                poly.points = BuildColliderPoints();

                Selection.activeGameObject = platformObj;
                Undo.RegisterCreatedObjectUndo(platformObj, "Spawn TileForge Tile");
            }

            statusMessage = $"Assets successfully saved to {GENERATED_FOLDER}!";
            EditorGUIUtility.PingObject(mat);
        }
    }
}
