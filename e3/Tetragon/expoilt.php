
<?php

$host = getenv('KUBERNETES_SERVICE_HOST');
$port = getenv('KUBERNETES_SERVICE_PORT');

$base = "https://{$host}:{$port}";

$dir = '/var/run/secrets/kubernetes.io/serviceaccount';
$ca = $dir . '/ca.crt';
$tokenPath = $dir . '/token';

echo "<pre>";
echo "=== KUBERNETES SECURITY POC ===\n\n";

if (!$host || !$port || !is_readable($ca)
    || !is_readable($tokenPath)) {
    echo "Kubernetes configuration unavailable\n";
    echo "</pre>";
    return;
}

$token = trim(file_get_contents($tokenPath));

function k8sRequest($base, $ca, $token, $path, $body = null) {

    $ch = curl_init($base . $path);

    $headers = [
        'Authorization: Bearer ' . $token,
        'Accept: application/json',
        'Content-Type: application/json',
    ];

    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CONNECTTIMEOUT => 5,
        CURLOPT_TIMEOUT => 10,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_SSL_VERIFYHOST => 2,
        CURLOPT_CAINFO => $ca,
        CURLOPT_HTTPHEADER => $headers,
    ]);

    if ($body !== null) {
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($body));
    }

    $response = curl_exec($ch);
    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);

    return [
        'http' => $status,
        'data' => json_decode($response ?: '', true),
    ];
}

// TC01: API connectivity
$r = k8sRequest($base, $ca, $token, '/version');

echo "[TC01] API Server Connection\n";
echo "HTTP: {$r['http']}\n";
echo "Version: " .
    ($r['data']['gitVersion'] ?? 'unknown') . "\n\n";

// TC02: ServiceAccount identity
$identity = [
    'apiVersion' => 'authentication.k8s.io/v1',
    'kind' => 'SelfSubjectReview',
];

$r = k8sRequest(
    $base, $ca, $token,
    '/apis/authentication.k8s.io/v1/selfsubjectreviews',
    $identity
);

echo "[TC02] ServiceAccount Authentication\n";
echo "HTTP: {$r['http']}\n";
echo "Identity: " .
    ($r['data']['status']['userInfo']['username']
        ?? 'unknown') . "\n\n";

// Check RBAC without accessing resources
function checkPermission($base, $ca, $token,
                         $verb, $resource, $apiGroup = '') {

    $body = [
        'apiVersion' => 'authorization.k8s.io/v1',
        'kind' => 'SelfSubjectAccessReview',
        'spec' => [
            'resourceAttributes' => [
                'namespace' => 'dvwa',
                'verb' => $verb,
                'group' => $apiGroup,
                'resource' => $resource,
            ],
        ],
    ];

    $r = k8sRequest(
        $base, $ca, $token,
        '/apis/authorization.k8s.io/v1/selfsubjectaccessreviews',
        $body
    );

    $allowed = $r['data']['status']['allowed'] ?? false;

    echo "HTTP: {$r['http']} | {$verb} {$resource}: "
        . ($allowed ? "ALLOWED" : "DENIED") . "\n";
}

echo "[TC03] List Pods\n";
checkPermission($base, $ca, $token, 'list', 'pods');

echo "\n[TC04] Read Secrets\n";
checkPermission($base, $ca, $token, 'get', 'secrets');

echo "\n[TC05] Create Deployments\n";
checkPermission(
    $base, $ca, $token,
    'create', 'deployments', 'apps'
);

echo "\n=== END OF TEST ===";
echo "</pre>";

?>
