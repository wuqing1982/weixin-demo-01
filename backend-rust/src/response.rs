use axum::http::StatusCode;
use axum::Json;
use serde::Serialize;
use serde_json::{json, Value};

pub fn success<T: Serialize>(data: T) -> Json<Value> {
    Json(json!({
        "code": 0,
        "data": data,
        "message": "ok"
    }))
}

pub fn success_empty() -> Json<Value> {
    Json(json!({
        "code": 0,
        "data": null,
        "message": "ok"
    }))
}

pub fn fail(status: StatusCode, code: i32, message: &str) -> (StatusCode, Json<Value>) {
    (status, Json(json!({
        "code": code,
        "data": null,
        "message": message
    })))
}
