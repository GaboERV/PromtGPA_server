from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from ....domain.exceptions import (
    UsuarioNoEncontradoError,
    CredencialesInvalidasError,
    TokenInvalidoError,
    CuadernoNoEncontradoError,
    SalaNoEncontradaError,
    ExamenNoEncontradoError,
    IntentoNoEncontradoError,
    PermisoDenegadoError
)

def register_error_handlers(app: FastAPI) -> None:
    """
    Registra manejadores de excepciones globales para capturar excepciones del dominio
    y transformarlas en respuestas JSON formateadas con códigos HTTP adecuados.
    """
    
    @app.exception_handler(UsuarioNoEncontradoError)
    async def usuario_no_encontrado_handler(request: Request, exc: UsuarioNoEncontradoError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": exc.mensaje}
        )

    @app.exception_handler(CredencialesInvalidasError)
    async def credenciales_invalidas_handler(request: Request, exc: CredencialesInvalidasError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": exc.mensaje}
        )

    @app.exception_handler(TokenInvalidoError)
    async def token_invalido_handler(request: Request, exc: TokenInvalidoError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": exc.mensaje}
        )

    @app.exception_handler(CuadernoNoEncontradoError)
    async def cuaderno_no_encontrado_handler(request: Request, exc: CuadernoNoEncontradoError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": exc.mensaje}
        )

    @app.exception_handler(SalaNoEncontradaError)
    async def sala_no_encontrada_handler(request: Request, exc: SalaNoEncontradaError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": exc.mensaje}
        )

    @app.exception_handler(ExamenNoEncontradoError)
    async def examen_no_encontrado_handler(request: Request, exc: ExamenNoEncontradoError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": exc.mensaje}
        )

    @app.exception_handler(IntentoNoEncontradoError)
    async def intento_no_encontrado_handler(request: Request, exc: IntentoNoEncontradoError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": exc.mensaje}
        )

    @app.exception_handler(PermisoDenegadoError)
    async def permiso_denegado_handler(request: Request, exc: PermisoDenegadoError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": exc.mensaje}
        )
