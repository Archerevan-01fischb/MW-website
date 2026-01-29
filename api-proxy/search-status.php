<?php
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

$job_id = isset($_GET['job_id']) ? $_GET['job_id'] : '';
if (empty($job_id)) {
    http_response_code(400);
    echo json_encode(['error' => 'job_id required']);
    exit;
}

$ch = curl_init('http://localhost:8500/api/search/status/' . urlencode($job_id));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 30);
$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);
http_response_code($httpCode);
echo $response;
