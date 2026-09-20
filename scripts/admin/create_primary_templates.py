from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


EXPECTED_POINTS = [1, 2, 3, 3, 3, 3, 3, 3]
EXPECTED_TOTAL_POINTS = sum(EXPECTED_POINTS)

PRIMARY_TEMPLATE_CATALOG = json.loads(
    r'''[{"template":{"name":"Primaria 1.º - Retos de atención lectora - A","description":"Banco original de práctica y pilotaje para 1.º de primaria. Atención a letras y sílabas cortas; frases breves con palabras parecidas. 8 ejercicios; pesos: 1, 2, 3, 3, 3, 3, 3, 3. Grado y dificultad propuestos, pendientes de pilotaje; no es una aplicación del PROLEC-R.","version":1},"exercises":[{"key":"G01-E01","body":{"type":"MULTIPLE_CHOICE","title":"G01-E01 | 1.º primaria | Encuentra la palabra","instructions":"Lee con atención y marca una sola respuesta.","stimulus_type":"TEXT","response_type":"SELECTION","difficulty_level":1,"mc_question":{"question_text":"Mira el modelo: pala. Marca la palabra exactamente igual.","options":[{"text":"pala","is_correct":true,"order_index":1},{"text":"pata","is_correct":false,"order_index":2},{"text":"bala","is_correct":false,"order_index":3},{"text":"lapa","is_correct":false,"order_index":4}]}},"attach":{"order_index":1,"points":1,"is_required":true}},{"key":"G01-E02","body":{"type":"ORDER_SYLLABLES","title":"G01-E02 | 1.º primaria | Ordena las sílabas - pato","instructions":"Ordena todas las sílabas para formar la palabra que corresponde a la pista.","stimulus_type":"TEXT","response_type":"ORDERING","difficulty_level":1,"os_question":{"question_text":"Ordena las sílabas. Pista: Es un ave que nada y dice «cuac».","correct_word":"pato","syllables_json":["to","pa"]}},"attach":{"order_index":2,"points":2,"is_required":true}},{"key":"G01-E03","body":{"type":"READING_SPEAKING","title":"G01-E03 | 1.º primaria | La pata de Pati","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":1,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"Pati mira la pata del pato.","language_code":"es-PE","expected_text":"Pati mira la pata del pato."}},"attach":{"order_index":3,"points":3,"is_required":true}},{"key":"G01-E04","body":{"type":"READING_SPEAKING","title":"G01-E04 | 1.º primaria | Lola y la luna","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":1,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"Lola mira la luna en la loma.","language_code":"es-PE","expected_text":"Lola mira la luna en la loma."}},"attach":{"order_index":4,"points":3,"is_required":true}},{"key":"G01-E05","body":{"type":"READING_SPEAKING","title":"G01-E05 | 1.º primaria | Dado y dedo","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":1,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"Dina toca el dado con el dedo.","language_code":"es-PE","expected_text":"Dina toca el dado con el dedo."}},"attach":{"order_index":5,"points":3,"is_required":true}},{"key":"G01-E06","body":{"type":"READING_WRITING","title":"G01-E06 | 1.º primaria | Pala y pata","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":1,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"pala y pata","language_code":"es-PE","expected_text":"pala y pata"}},"attach":{"order_index":6,"points":3,"is_required":true}},{"key":"G01-E07","body":{"type":"READING_WRITING","title":"G01-E07 | 1.º primaria | Dado y dedo","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":1,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"dado y dedo","language_code":"es-PE","expected_text":"dado y dedo"}},"attach":{"order_index":7,"points":3,"is_required":true}},{"key":"G01-E08","body":{"type":"READING_WRITING","title":"G01-E08 | 1.º primaria | La luna de Lola","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":1,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"Lola mira la luna.","language_code":"es-PE","expected_text":"Lola mira la luna."}},"attach":{"order_index":8,"points":3,"is_required":true}}]},{"template":{"name":"Primaria 2.º - Retos de atención lectora - A","description":"Banco original de práctica y pilotaje para 2.º de primaria. Palabras próximas, grupos consonánticos sencillos y seguimiento de una acción. 8 ejercicios; pesos: 1, 2, 3, 3, 3, 3, 3, 3. Grado y dificultad propuestos, pendientes de pilotaje; no es una aplicación del PROLEC-R.","version":1},"exercises":[{"key":"G02-E01","body":{"type":"MULTIPLE_CHOICE","title":"G02-E01 | 2.º primaria | Rana y rama","instructions":"Lee con atención y marca una sola respuesta.","stimulus_type":"TEXT","response_type":"SELECTION","difficulty_level":2,"mc_question":{"question_text":"Lee: «La rana mira la rama». ¿Qué mira la rana?","options":[{"text":"La rana.","is_correct":false,"order_index":1},{"text":"La rama.","is_correct":true,"order_index":2},{"text":"La rampa.","is_correct":false,"order_index":3},{"text":"La lana.","is_correct":false,"order_index":4}]}},"attach":{"order_index":1,"points":1,"is_required":true}},{"key":"G02-E02","body":{"type":"ORDER_SYLLABLES","title":"G02-E02 | 2.º primaria | Ordena las sílabas - maleta","instructions":"Ordena todas las sílabas para formar la palabra que corresponde a la pista.","stimulus_type":"TEXT","response_type":"ORDERING","difficulty_level":2,"os_question":{"question_text":"Ordena las sílabas. Pista: Sirve para llevar ropa cuando viajas.","correct_word":"maleta","syllables_json":["ta","ma","le"]}},"attach":{"order_index":2,"points":2,"is_required":true}},{"key":"G02-E03","body":{"type":"READING_SPEAKING","title":"G02-E03 | 2.º primaria | Rita y la rueda","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":2,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"Rita retira la rueda rota de su carrito rojo.","language_code":"es-PE","expected_text":"Rita retira la rueda rota de su carrito rojo."}},"attach":{"order_index":3,"points":3,"is_required":true}},{"key":"G02-E04","body":{"type":"READING_SPEAKING","title":"G02-E04 | 2.º primaria | Pablo y el plato","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":2,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"Pablo pone un plato blanco sobre la mesa blanca.","language_code":"es-PE","expected_text":"Pablo pone un plato blanco sobre la mesa blanca."}},"attach":{"order_index":4,"points":3,"is_required":true}},{"key":"G02-E05","body":{"type":"READING_SPEAKING","title":"G02-E05 | 2.º primaria | Camila camina","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":2,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"Camila camina con calma por el camino de casa.","language_code":"es-PE","expected_text":"Camila camina con calma por el camino de casa."}},"attach":{"order_index":5,"points":3,"is_required":true}},{"key":"G02-E06","body":{"type":"READING_WRITING","title":"G02-E06 | 2.º primaria | Rama y rana","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":2,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"La rana salta a la rama.","language_code":"es-PE","expected_text":"La rana salta a la rama."}},"attach":{"order_index":6,"points":3,"is_required":true}},{"key":"G02-E07","body":{"type":"READING_WRITING","title":"G02-E07 | 2.º primaria | Pelo y perro","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":2,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"El perro pierde pelo.","language_code":"es-PE","expected_text":"El perro pierde pelo."}},"attach":{"order_index":7,"points":3,"is_required":true}},{"key":"G02-E08","body":{"type":"READING_WRITING","title":"G02-E08 | 2.º primaria | Copa y poca","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":2,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"Paco pone poca agua en la copa.","language_code":"es-PE","expected_text":"Paco pone poca agua en la copa."}},"attach":{"order_index":8,"points":3,"is_required":true}}]},{"template":{"name":"Primaria 3.º - Retos de atención lectora - A","description":"Banco original de práctica y pilotaje para 3.º de primaria. Grupos consonánticos, terminaciones semejantes y comprensión de quién recibe una acción. 8 ejercicios; pesos: 1, 2, 3, 3, 3, 3, 3, 3. Grado y dificultad propuestos, pendientes de pilotaje; no es una aplicación del PROLEC-R.","version":1},"exercises":[{"key":"G03-E01","body":{"type":"MULTIPLE_CHOICE","title":"G03-E01 | 3.º primaria | El libro prestado","instructions":"Lee con atención y marca una sola respuesta.","stimulus_type":"TEXT","response_type":"SELECTION","difficulty_level":3,"mc_question":{"question_text":"Lee: «El primo de Bruno presta un libro a Brenda». ¿Quién recibe el libro?","options":[{"text":"El primo de Bruno.","is_correct":false,"order_index":1},{"text":"Bruno.","is_correct":false,"order_index":2},{"text":"Brenda.","is_correct":true,"order_index":3},{"text":"Los tres.","is_correct":false,"order_index":4}]}},"attach":{"order_index":1,"points":1,"is_required":true}},{"key":"G03-E02","body":{"type":"ORDER_SYLLABLES","title":"G03-E02 | 3.º primaria | Ordena las sílabas - palmera","instructions":"Ordena todas las sílabas para formar la palabra que corresponde a la pista.","stimulus_type":"TEXT","response_type":"ORDERING","difficulty_level":3,"os_question":{"question_text":"Ordena las sílabas. Pista: Es un árbol de tronco largo que puede dar cocos.","correct_word":"palmera","syllables_json":["ra","pal","me"]}},"attach":{"order_index":2,"points":2,"is_required":true}},{"key":"G03-E03","body":{"type":"READING_SPEAKING","title":"G03-E03 | 3.º primaria | Bruno y Brenda","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":3,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"Bruno presta un libro a Brenda, y Brenda lo guarda.","language_code":"es-PE","expected_text":"Bruno presta un libro a Brenda, y Brenda lo guarda."}},"attach":{"order_index":3,"points":3,"is_required":true}},{"key":"G03-E04","body":{"type":"READING_SPEAKING","title":"G03-E04 | 3.º primaria | Clara y el clavo","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":3,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"Clara clava un clavo corto junto a un clavo curvo.","language_code":"es-PE","expected_text":"Clara clava un clavo corto junto a un clavo curvo."}},"attach":{"order_index":4,"points":3,"is_required":true}},{"key":"G03-E05","body":{"type":"READING_SPEAKING","title":"G03-E05 | 3.º primaria | La vaca y la cabra","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":3,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"La vaca brava va al campo y la cabra va al corral.","language_code":"es-PE","expected_text":"La vaca brava va al campo y la cabra va al corral."}},"attach":{"order_index":5,"points":3,"is_required":true}},{"key":"G03-E06","body":{"type":"READING_WRITING","title":"G03-E06 | 3.º primaria | Plato y pasto","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":3,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"El plato de plástico cayó al pasto.","language_code":"es-PE","expected_text":"El plato de plástico cayó al pasto."}},"attach":{"order_index":6,"points":3,"is_required":true}},{"key":"G03-E07","body":{"type":"READING_WRITING","title":"G03-E07 | 3.º primaria | Brocha y bruja","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":3,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"Bruno guarda la brocha de la bruja.","language_code":"es-PE","expected_text":"Bruno guarda la brocha de la bruja."}},"attach":{"order_index":7,"points":3,"is_required":true}},{"key":"G03-E08","body":{"type":"READING_WRITING","title":"G03-E08 | 3.º primaria | Llama y llave","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":3,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"Clara llama a Carla y le pide la llave.","language_code":"es-PE","expected_text":"Clara llama a Carla y le pide la llave."}},"attach":{"order_index":8,"points":3,"is_required":true}}]},{"template":{"name":"Primaria 4.º - Retos de atención lectora - A","description":"Banco original de práctica y pilotaje para 4.º de primaria. Orden poco habitual de los participantes, palabras largas y pausas con sentido. 8 ejercicios; pesos: 1, 2, 3, 3, 3, 3, 3, 3. Grado y dificultad propuestos, pendientes de pilotaje; no es una aplicación del PROLEC-R.","version":1},"exercises":[{"key":"G04-E01","body":{"type":"MULTIPLE_CHOICE","title":"G04-E01 | 4.º primaria | Quién entrevista","instructions":"Lee con atención y marca una sola respuesta.","stimulus_type":"TEXT","response_type":"SELECTION","difficulty_level":4,"mc_question":{"question_text":"Lee: «A la reportera la entrevista el escritor». ¿Quién hace las preguntas?","options":[{"text":"La reportera.","is_correct":false,"order_index":1},{"text":"La escritora.","is_correct":false,"order_index":2},{"text":"El lector.","is_correct":false,"order_index":3},{"text":"El escritor.","is_correct":true,"order_index":4}]}},"attach":{"order_index":1,"points":1,"is_required":true}},{"key":"G04-E02","body":{"type":"ORDER_SYLLABLES","title":"G04-E02 | 4.º primaria | Ordena las sílabas - biblioteca","instructions":"Ordena todas las sílabas para formar la palabra que corresponde a la pista.","stimulus_type":"TEXT","response_type":"ORDERING","difficulty_level":4,"os_question":{"question_text":"Ordena las sílabas. Pista: Es el lugar donde puedes consultar o pedir libros prestados.","correct_word":"biblioteca","syllables_json":["te","ca","bi","blio"]}},"attach":{"order_index":2,"points":2,"is_required":true}},{"key":"G04-E03","body":{"type":"READING_SPEAKING","title":"G04-E03 | 4.º primaria | La perra de Rosa","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":4,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"La perra de Rosa corre por la tierra, pero Rosa camina por la acera.","language_code":"es-PE","expected_text":"La perra de Rosa corre por la tierra, pero Rosa camina por la acera."}},"attach":{"order_index":3,"points":3,"is_required":true}},{"key":"G04-E04","body":{"type":"READING_SPEAKING","title":"G04-E04 | 4.º primaria | Tomás y las tazas","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":4,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"Tomás toma tres tazas pequeñas, mientras Teresa toma tres tapas del mismo tamaño.","language_code":"es-PE","expected_text":"Tomás toma tres tazas pequeñas, mientras Teresa toma tres tapas del mismo tamaño."}},"attach":{"order_index":4,"points":3,"is_required":true}},{"key":"G04-E05","body":{"type":"READING_SPEAKING","title":"G04-E05 | 4.º primaria | La cabra en el cuento","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":4,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"En el cuento, la cabra brava cava cerca de la cabaña para buscar una caja.","language_code":"es-PE","expected_text":"En el cuento, la cabra brava cava cerca de la cabaña para buscar una caja."}},"attach":{"order_index":5,"points":3,"is_required":true}},{"key":"G04-E06","body":{"type":"READING_WRITING","title":"G04-E06 | 4.º primaria | La llave de Carla","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":4,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"Carla encontró la llave que Clara dejó junto a la caja.","language_code":"es-PE","expected_text":"Carla encontró la llave que Clara dejó junto a la caja."}},"attach":{"order_index":6,"points":3,"is_required":true}},{"key":"G04-E07","body":{"type":"READING_WRITING","title":"G04-E07 | 4.º primaria | Un tubo y un problema","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":4,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"El plomero tuvo un problema con un tubo de plástico.","language_code":"es-PE","expected_text":"El plomero tuvo un problema con un tubo de plástico."}},"attach":{"order_index":7,"points":3,"is_required":true}},{"key":"G04-E08","body":{"type":"READING_WRITING","title":"G04-E08 | 4.º primaria | Público y publicó","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":4,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"El público aplaudió cuando Paula publicó el resultado.","language_code":"es-PE","expected_text":"El público aplaudió cuando Paula publicó el resultado."}},"attach":{"order_index":8,"points":3,"is_required":true}}]},{"template":{"name":"Primaria 5.º - Retos de atención lectora - A","description":"Banco original de práctica y pilotaje para 5.º de primaria. Integración de relaciones, negación, palabras semejantes y acentuación en contexto. 8 ejercicios; pesos: 1, 2, 3, 3, 3, 3, 3, 3. Grado y dificultad propuestos, pendientes de pilotaje; no es una aplicación del PROLEC-R.","version":1},"exercises":[{"key":"G05-E01","body":{"type":"MULTIPLE_CHOICE","title":"G05-E01 | 5.º primaria | Lila, Lina y Nora","instructions":"Lee con atención y marca una sola respuesta.","stimulus_type":"TEXT","response_type":"SELECTION","difficulty_level":5,"mc_question":{"question_text":"Lee: «Nora llegó después de Lila, pero antes de Lina». ¿Quién llegó segunda?","options":[{"text":"Nora.","is_correct":true,"order_index":1},{"text":"Lila.","is_correct":false,"order_index":2},{"text":"Lina.","is_correct":false,"order_index":3},{"text":"Las tres llegaron juntas.","is_correct":false,"order_index":4}]}},"attach":{"order_index":1,"points":1,"is_required":true}},{"key":"G05-E02","body":{"type":"ORDER_SYLLABLES","title":"G05-E02 | 5.º primaria | Ordena las sílabas - termómetro","instructions":"Ordena todas las sílabas para formar la palabra que corresponde a la pista.","stimulus_type":"TEXT","response_type":"ORDERING","difficulty_level":5,"os_question":{"question_text":"Ordena las sílabas. Pista: Es un instrumento que sirve para medir la temperatura.","correct_word":"termómetro","syllables_json":["me","tro","ter","mó"]}},"attach":{"order_index":2,"points":2,"is_required":true}},{"key":"G05-E03","body":{"type":"READING_SPEAKING","title":"G05-E03 | 5.º primaria | Prudencio comprende","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":5,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"Prudencio comprende pronto la primera pregunta, pero prefiere preguntarle a la profesora por qué la segunda pregunta parece tan parecida.","language_code":"es-PE","expected_text":"Prudencio comprende pronto la primera pregunta, pero prefiere preguntarle a la profesora por qué la segunda pregunta parece tan parecida."}},"attach":{"order_index":3,"points":3,"is_required":true}},{"key":"G05-E04","body":{"type":"READING_SPEAKING","title":"G05-E04 | 5.º primaria | La puerta del puerto","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":5,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"Cerca de la puerta del puerto, Pedro perdió una cuerda corta; Petra encontró la cuerda y se la devolvió.","language_code":"es-PE","expected_text":"Cerca de la puerta del puerto, Pedro perdió una cuerda corta; Petra encontró la cuerda y se la devolvió."}},"attach":{"order_index":4,"points":3,"is_required":true}},{"key":"G05-E05","body":{"type":"READING_SPEAKING","title":"G05-E05 | 5.º primaria | El perro que corre","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":5,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"El perro que persigue al gato lleva una cinta roja; el gato, que corre delante, lleva una cinta rosa.","language_code":"es-PE","expected_text":"El perro que persigue al gato lleva una cinta roja; el gato, que corre delante, lleva una cinta rosa."}},"attach":{"order_index":5,"points":3,"is_required":true}},{"key":"G05-E06","body":{"type":"READING_WRITING","title":"G05-E06 | 5.º primaria | La práctica","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":5,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"La práctica mejora cuando Paula practica con paciencia.","language_code":"es-PE","expected_text":"La práctica mejora cuando Paula practica con paciencia."}},"attach":{"order_index":6,"points":3,"is_required":true}},{"key":"G05-E07","body":{"type":"READING_WRITING","title":"G05-E07 | 5.º primaria | El hecho","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":5,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"He hecho la tarea y echo los papeles en la caja.","language_code":"es-PE","expected_text":"He hecho la tarea y echo los papeles en la caja."}},"attach":{"order_index":7,"points":3,"is_required":true}},{"key":"G05-E08","body":{"type":"READING_WRITING","title":"G05-E08 | 5.º primaria | El abrigo de Abril","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":5,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"Abril abrió el armario y abrigó a su hermano antes de salir.","language_code":"es-PE","expected_text":"Abril abrió el armario y abrigó a su hermano antes de salir."}},"attach":{"order_index":8,"points":3,"is_required":true}}]},{"template":{"name":"Primaria 6.º - Retos de atención lectora - A","description":"Banco original de práctica y pilotaje para 6.º de primaria. Condiciones explícitas, vocabulario parecido y oraciones con subordinación y puntuación. 8 ejercicios; pesos: 1, 2, 3, 3, 3, 3, 3, 3. Grado y dificultad propuestos, pendientes de pilotaje; no es una aplicación del PROLEC-R.","version":1},"exercises":[{"key":"G06-E01","body":{"type":"MULTIPLE_CHOICE","title":"G06-E01 | 6.º primaria | El día del ensayo","instructions":"Lee con atención y marca una sola respuesta.","stimulus_type":"TEXT","response_type":"SELECTION","difficulty_level":5,"mc_question":{"question_text":"Lee el aviso: «Si el jueves llueve, el ensayo será el viernes; si no llueve, será el jueves». El jueves no llovió. ¿Qué día corresponde al ensayo según el aviso?","options":[{"text":"El viernes.","is_correct":false,"order_index":1},{"text":"El jueves.","is_correct":true,"order_index":2},{"text":"El jueves y el viernes.","is_correct":false,"order_index":3},{"text":"Ninguno: el ensayo se cancela.","is_correct":false,"order_index":4}]}},"attach":{"order_index":1,"points":1,"is_required":true}},{"key":"G06-E02","body":{"type":"ORDER_SYLLABLES","title":"G06-E02 | 6.º primaria | Ordena las sílabas - transformación","instructions":"Ordena todas las sílabas para formar la palabra que corresponde a la pista.","stimulus_type":"TEXT","response_type":"ORDERING","difficulty_level":5,"os_question":{"question_text":"Ordena las sílabas. Pista: Es un cambio de forma o de estado. La palabra termina en -ción.","correct_word":"transformación","syllables_json":["ción","for","trans","ma"]}},"attach":{"order_index":2,"points":2,"is_required":true}},{"key":"G06-E03","body":{"type":"READING_SPEAKING","title":"G06-E03 | 6.º primaria | El informe de Patricia","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":5,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"Patricia presenta una propuesta precisa, pero Priscila interpreta otra propuesta parecida. Antes de responder, las dos repasan el primer párrafo y comprueban cuál era la pregunta.","language_code":"es-PE","expected_text":"Patricia presenta una propuesta precisa, pero Priscila interpreta otra propuesta parecida. Antes de responder, las dos repasan el primer párrafo y comprueban cuál era la pregunta."}},"attach":{"order_index":3,"points":3,"is_required":true}},{"key":"G06-E04","body":{"type":"READING_SPEAKING","title":"G06-E04 | 6.º primaria | Plantas trasplantadas","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":5,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"El jardinero que trasplantó las plantas pequeñas explicó que las plantas trasplantadas necesitan sombra durante los primeros días, aunque las plantas grandes permanezcan al sol.","language_code":"es-PE","expected_text":"El jardinero que trasplantó las plantas pequeñas explicó que las plantas trasplantadas necesitan sombra durante los primeros días, aunque las plantas grandes permanezcan al sol."}},"attach":{"order_index":4,"points":3,"is_required":true}},{"key":"G06-E05","body":{"type":"READING_SPEAKING","title":"G06-E05 | 6.º primaria | El traje junto a la entrada","instructions":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","stimulus_type":"TEXT","response_type":"AUDIO","difficulty_level":5,"prompt_exercise":{"prompt_text":"Lee el texto en voz alta con calma y respeta los signos de puntuación.","text_to_show":"Cuando traje el traje que Teresa había dejado detrás de la puerta, advertí que otro traje parecido estaba doblado dentro de una bolsa junto a la entrada.","language_code":"es-PE","expected_text":"Cuando traje el traje que Teresa había dejado detrás de la puerta, advertí que otro traje parecido estaba doblado dentro de una bolsa junto a la entrada."}},"attach":{"order_index":5,"points":3,"is_required":true}},{"key":"G06-E06","body":{"type":"READING_WRITING","title":"G06-E06 | 6.º primaria | Tú y tu respuesta","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":5,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"Tú revisas tu respuesta; él revisa el ejemplo antes de explicar por qué cambió.","language_code":"es-PE","expected_text":"Tú revisas tu respuesta; él revisa el ejemplo antes de explicar por qué cambió."}},"attach":{"order_index":6,"points":3,"is_required":true}},{"key":"G06-E07","body":{"type":"READING_WRITING","title":"G06-E07 | 6.º primaria | Una descripción precisa","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":5,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"La descripción del experimento parecía precisa, pero la explicación del procedimiento resultó demasiado imprecisa.","language_code":"es-PE","expected_text":"La descripción del experimento parecía precisa, pero la explicación del procedimiento resultó demasiado imprecisa."}},"attach":{"order_index":7,"points":3,"is_required":true}},{"key":"G06-E08","body":{"type":"READING_WRITING","title":"G06-E08 | 6.º primaria | Sí y si","instructions":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","stimulus_type":"TEXT","response_type":"WRITING_IMAGE","difficulty_level":5,"prompt_exercise":{"prompt_text":"Copia el texto tal como aparece. Conserva las letras, los espacios y los signos.","text_to_show":"Si Sara dice que sí, iremos; si dice que no, seguiremos aquí hasta recibir otra respuesta.","language_code":"es-PE","expected_text":"Si Sara dice que sí, iremos; si dice que no, seguiremos aquí hasta recibir otra respuesta."}},"attach":{"order_index":8,"points":3,"is_required":true}}]}]'''
)


class AdminScriptError(RuntimeError):
    pass


@dataclass
class ApiClient:
    base_url: str
    token: str

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    def get(self, path: str, query: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, query=query)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request("POST", path, payload=payload)

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"

        body = None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=30) as response:
                text = response.read().decode("utf-8")
        except HTTPError as exc:
            response_text = exc.read().decode("utf-8", errors="replace")
            print_api_error(method, url, exc.code, response_text)
            raise AdminScriptError(f"{method} {url} failed with {exc.code}") from exc
        except URLError as exc:
            print(f"ERROR {method} {url}", file=sys.stderr)
            print(f"Network error: {exc}", file=sys.stderr)
            raise AdminScriptError(f"{method} {url} failed") from exc

        if not text:
            return None
        return json.loads(text)


def print_api_error(method: str, url: str, status_code: int, response_text: str) -> None:
    print(f"ERROR {method} {url}", file=sys.stderr)
    print(f"status_code={status_code}", file=sys.stderr)
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError:
        print(response_text, file=sys.stderr)
    else:
        print(json.dumps(parsed, ensure_ascii=False, indent=2), file=sys.stderr)


def validate_catalog() -> None:
    if len(PRIMARY_TEMPLATE_CATALOG) != 6:
        raise AdminScriptError("Catalog must contain exactly 6 templates.")

    for template_entry in PRIMARY_TEMPLATE_CATALOG:
        exercises = template_entry["exercises"]
        if len(exercises) != 8:
            raise AdminScriptError(f"{template_entry['template']['name']} must contain 8 exercises.")
        points = [item["attach"]["points"] for item in exercises]
        order_indexes = [item["attach"]["order_index"] for item in exercises]
        if points != EXPECTED_POINTS:
            raise AdminScriptError(f"{template_entry['template']['name']} has invalid points: {points}")
        if order_indexes != list(range(1, 9)):
            raise AdminScriptError(f"{template_entry['template']['name']} has invalid order: {order_indexes}")

        for item in exercises:
            body = item["body"]
            difficulty = body.get("difficulty_level")
            if difficulty is not None and not 1 <= difficulty <= 5:
                raise AdminScriptError(f"{item['key']} difficulty_level must be between 1 and 5.")
            if body["type"] in {"READING_SPEAKING", "READING_WRITING"}:
                prompt = body.get("prompt_exercise")
                if not prompt:
                    raise AdminScriptError(f"{item['key']} must use prompt_exercise.")
                for field in ("prompt_text", "text_to_show", "language_code", "expected_text"):
                    if field not in prompt:
                        raise AdminScriptError(f"{item['key']} prompt_exercise missing {field}.")
                if prompt["language_code"] != "es-PE":
                    raise AdminScriptError(f"{item['key']} language_code must be es-PE.")
                if "rs_prompt" in body or "rw_prompt" in body:
                    raise AdminScriptError(f"{item['key']} must not use rs_prompt or rw_prompt.")
            if body["type"] == "ORDER_SYLLABLES" and "syllables_json" not in body.get("os_question", {}):
                raise AdminScriptError(f"{item['key']} must include os_question.syllables_json.")
            if body["type"] == "MULTIPLE_CHOICE" and "options" not in body.get("mc_question", {}):
                raise AdminScriptError(f"{item['key']} must include mc_question.options.")


def print_dry_run() -> None:
    print("DRY-RUN: no se creara nada. Use --execute para aplicar cambios.")
    for template_entry in PRIMARY_TEMPLATE_CATALOG:
        template = template_entry["template"]
        print(f"\nTemplate: {template['name']}")
        print(f"  version={template['version']} total_points={EXPECTED_TOTAL_POINTS}")
        for item in template_entry["exercises"]:
            body = item["body"]
            attach = item["attach"]
            print(
                "  "
                f"{item['key']}: {body['type']} | {body['title']} | "
                f"order={attach['order_index']} points={attach['points']} required={attach['is_required']}"
            )


def active_template_by_name(client: ApiClient, name: str) -> dict[str, Any] | None:
    templates = client.get("/api/v1/assessments/templates")
    return next((item for item in templates if item.get("is_active") and item.get("name") == name), None)


def find_exercise_by_title(client: ApiClient, title: str) -> dict[str, Any] | None:
    result = client.get("/api/v1/assessments/exercises", {"q": title, "limit": 100})
    matches = [item for item in result.get("items", []) if item.get("title") == title and item.get("is_active")]
    if len(matches) > 1:
        print(f"WARNING: hay {len(matches)} ejercicios activos con title exacto; se reutiliza el mas reciente: {title}")
    return matches[0] if matches else None


def ensure_template(client: ApiClient, template_body: dict[str, Any]) -> tuple[str, bool]:
    existing = active_template_by_name(client, template_body["name"])
    if existing:
        print(f"WARNING: plantilla activa existente, se reutiliza: {template_body['name']}")
        return existing["template_id"], False

    created = client.post("/api/v1/assessments/templates", template_body)
    print(f"CREATED template: {template_body['name']} -> {created['template_id']}")
    return created["template_id"], True


def ensure_exercise(client: ApiClient, item: dict[str, Any]) -> tuple[str, bool]:
    title = item["body"]["title"]
    existing = find_exercise_by_title(client, title)
    if existing:
        print(f"REUSED exercise: {item['key']} -> {existing['exercise_id']} | {title}")
        return existing["exercise_id"], False

    created = client.post("/api/v1/assessments/exercises", item["body"])
    print(f"CREATED exercise: {item['key']} -> {created['exercise_id']} | {title}")
    return created["exercise_id"], True


def ensure_template_can_be_attached(client: ApiClient, template_id: str, template_name: str) -> bool:
    detail = client.get(f"/api/v1/assessments/templates/{quote(template_id)}")
    count = detail.get("exercise_count", 0)
    if count == 0:
        return True
    if count == 8:
        print(f"SKIP: {template_name} ya tiene 8 ejercicios asociados.")
        validate_template_detail(detail)
        return False

    raise AdminScriptError(
        f"ABORT: {template_name} tiene {count} ejercicios asociados. "
        "No se completara una plantilla parcial para evitar mezclar contenido sin control."
    )


def attach_exercises(client: ApiClient, template_id: str, items: list[dict[str, Any]]) -> None:
    for item in items:
        exercise_id, _ = ensure_exercise(client, item)
        payload = {"exercise_id": exercise_id, **item["attach"]}
        client.post(f"/api/v1/assessments/templates/{quote(template_id)}/exercises", payload)
        print(
            "ATTACHED "
            f"{item['key']} order={payload['order_index']} points={payload['points']} exercise_id={exercise_id}"
        )


def validate_template_detail(detail: dict[str, Any]) -> None:
    name = detail["name"]
    exercises = sorted(detail.get("exercises", []), key=lambda item: item["order_index"])
    order_indexes = [item["order_index"] for item in exercises]
    points = [item["points"] for item in exercises]

    if detail.get("exercise_count") != 8:
        raise AdminScriptError(f"VERIFY FAILED {name}: exercise_count={detail.get('exercise_count')} expected=8")
    if detail.get("total_points") != EXPECTED_TOTAL_POINTS:
        raise AdminScriptError(
            f"VERIFY FAILED {name}: total_points={detail.get('total_points')} expected={EXPECTED_TOTAL_POINTS}"
        )
    if order_indexes != list(range(1, 9)):
        raise AdminScriptError(f"VERIFY FAILED {name}: order_index={order_indexes} expected=1..8")
    if points != EXPECTED_POINTS:
        raise AdminScriptError(f"VERIFY FAILED {name}: points={points} expected={EXPECTED_POINTS}")

    print(f"VERIFIED {name}: exercise_count=8 total_points={EXPECTED_TOTAL_POINTS} points={points}")


def execute(client: ApiClient) -> None:
    for template_entry in PRIMARY_TEMPLATE_CATALOG:
        template = template_entry["template"]
        template_id, _ = ensure_template(client, template)
        if ensure_template_can_be_attached(client, template_id, template["name"]):
            attach_exercises(client, template_id, template_entry["exercises"])

        detail = client.get(f"/api/v1/assessments/templates/{quote(template_id)}")
        validate_template_detail(detail)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or reuse the six primary reading templates and their exercises through the TamizAI API."
    )
    parser.add_argument("--base-url", required=True, help="API base URL, for example http://localhost:8000")
    parser.add_argument("--token", required=True, help="Bearer token with teacher/admin access")
    parser.add_argument("--execute", action="store_true", help="Create records. Without this flag, only dry-run.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_catalog()

    if not args.execute:
        print_dry_run()
        return 0

    client = ApiClient(base_url=args.base_url, token=args.token)
    execute(client)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AdminScriptError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
