from typing import List, Optional
from datetime import datetime
from ....domain.assessment_context.services.rag_engine_service import RAGEngineService
from ....domain.assessment_context.entities.examen import Examen, PreguntaExamen
from ....domain.notebook_context.entities.flashcard import Flashcard

class SimulatedRAGEngineService(RAGEngineService):
    """
    Simulador del Motor RAG de IA para desarrollo local.
    Analiza de forma ficticia el texto provisto y genera flashcards y exámenes consistentes.
    """
    async def generar_flashcards_por_contexto(
        self, 
        prompt: str, 
        archivo_ids: Optional[List[int]] = None, 
        texto_crudo: Optional[str] = None, 
        cantidad: int = 5
    ) -> List[Flashcard]:
        # Si no hay texto, usar un fallback consistente
        texto = texto_crudo or "Contexto vacío"
        print(f"[SimulatedRAG] Generando {cantidad} flashcards para prompt: '{prompt}' con longitud de texto: {len(texto)}...")
        
        flashcards = []
        for i in range(1, cantidad + 1):
            flashcards.append(Flashcard(
                id=None,
                question=f"Pregunta RAG #{i} generada en base a tu tema de estudio",
                answer=f"Respuesta automatizada #{i} construida a partir de los datos analizados",
                notebook_id=None,
                created_at=datetime.utcnow()
            ))
        return flashcards

    async def generar_examen_por_contexto(
        self, 
        prompt: str, 
        archivo_ids: Optional[List[int]] = None, 
        texto_crudo: Optional[str] = None
    ) -> Examen:
        texto = texto_crudo or "Contexto vacío"
        print(f"[SimulatedRAG] Generando examen de 3 preguntas de opción múltiple para prompt: '{prompt}'...")
        
        pregunta1 = PreguntaExamen(
            id=None,
            examen_id=None,
            question_text="¿Cuál de las siguientes afirmaciones describe la función principal del sistema RAG?",
            opciones={
                "A": "Generar texto aleatorio sin contexto previo.",
                "B": "Combinar la búsqueda semántica de documentos con modelos de lenguaje generativos.",
                "C": "Servir como base de datos relacional de alta velocidad.",
                "D": "Encriptar contraseñas de forma asíncrona."
            },
            correct_answer="B"
        )
        
        pregunta2 = PreguntaExamen(
            id=None,
            examen_id=None,
            question_text="En Arquitectura Hexagonal, ¿qué es la base de datos física?",
            opciones={
                "A": "Un puerto primario del dominio.",
                "B": "Un caso de uso de la aplicación.",
                "C": "Un adaptador secundario de infraestructura.",
                "D": "Una entidad del núcleo del negocio."
            },
            correct_answer="C"
        )

        pregunta3 = PreguntaExamen(
            id=None,
            examen_id=None,
            question_text="¿Para qué sirve el patrón Proxy en la Sala de Estudio del Invitado?",
            opciones={
                "A": "Para acelerar las consultas SQL de indexación.",
                "B": "Para proteger el cuaderno contra escrituras y modificaciones de participantes no autorizados.",
                "C": "Para hashear las contraseñas en hilos secundarios.",
                "D": "Para conectarse directamente a la VectorDB de Chroma."
            },
            correct_answer="B"
        )

        examen = Examen(
            id=None,
            title=f"Examen de práctica: {prompt[:30] if prompt else 'Generación RAG'}",
            notebook_id=None,
            preguntas=[pregunta1, pregunta2, pregunta3]
        )
        return examen
