use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use serde_json::json;

#[derive(Debug)]
pub enum AppError {
    BadRequest(String),
    Unauthorized(String),
    Forbidden(String),
    NotFound(String),
    Internal(String),
    ExternalApi(String),
}

impl std::fmt::Display for AppError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AppError::BadRequest(msg) => write!(f, "Bad request: {msg}"),
            AppError::Unauthorized(msg) => write!(f, "Unauthorized: {msg}"),
            AppError::Forbidden(msg) => write!(f, "Forbidden: {msg}"),
            AppError::NotFound(msg) => write!(f, "Not found: {msg}"),
            AppError::Internal(msg) => write!(f, "Internal error: {msg}"),
            AppError::ExternalApi(msg) => write!(f, "External API error: {msg}"),
        }
    }
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, code, message) = match &self {
            AppError::BadRequest(msg) => (StatusCode::BAD_REQUEST, 400, msg.clone()),
            AppError::Unauthorized(msg) => (StatusCode::UNAUTHORIZED, 4001, msg.clone()),
            AppError::Forbidden(msg) => (StatusCode::FORBIDDEN, 4003, msg.clone()),
            AppError::NotFound(msg) => (StatusCode::NOT_FOUND, 4004, msg.clone()),
            AppError::Internal(msg) => (StatusCode::INTERNAL_SERVER_ERROR, 5000, msg.clone()),
            AppError::ExternalApi(msg) => (StatusCode::BAD_GATEWAY, 5002, msg.clone()),
        };
        tracing::error!("Error: {self}");
        (status, axum::Json(json!({"code": code, "data": null, "message": message}))).into_response()
    }
}

impl From<sqlx::Error> for AppError {
    fn from(err: sqlx::Error) -> Self {
        AppError::Internal(err.to_string())
    }
}

impl From<std::io::Error> for AppError {
    fn from(err: std::io::Error) -> Self {
        AppError::Internal(err.to_string())
    }
}
