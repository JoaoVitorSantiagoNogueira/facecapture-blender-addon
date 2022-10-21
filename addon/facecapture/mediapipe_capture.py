#!/usr/bin/env python3

import cv2
import numpy as np
import mediapipe as mp

from .facegeometry import get_metric_landmarks, PCF, canonical_metric_landmarks, procrustes_landmark_basis


#função  para capturar face assincronamente usando mediapipe
# retorna função para realizar captura e função para liberar recursos
# lança excessão em caso de falha
def asyncCapture(camera_index):
    # Inicialização do contexto mediapipe
    mp_drawing = mp.solutions.drawing_utils
    mp_face_mesh = mp.solutions.face_mesh

    drawing_spec = mp_drawing.DrawingSpec(thickness=1, circle_radius=1)
    cap = cv2.VideoCapture(camera_index)

    points_idx = [33, 263, 61, 291, 199]
    points_idx = points_idx + [key for (key, val) in procrustes_landmark_basis]
    points_idx = list(set(points_idx))
    points_idx.sort()

    frame_height, frame_width, channels = (480, 640, 3)

    focal_length = frame_width
    center = (frame_width / 2, frame_height / 2)
    camera_matrix = np.array(
        [[focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]], dtype="double"
    )

    dist_coeff = np.zeros((4, 1))

    pcf = PCF(near=1, far=10000, frame_height=frame_height, frame_width=frame_width, fy=camera_matrix[1, 1])

    def getRigidInfo( faces ):

        iris_landmarks = faces.landmark[468:]
        face_landmarks = faces.landmark[:468]

        landmarks = np.array([(lm.x, lm.y, lm.z) for lm in face_landmarks]).T

        metric_landmarks, pose_transform_mat = get_metric_landmarks(landmarks.copy(), pcf)

        return {
            'landmark': landmarks.T,
            'iris': iris_landmarks ,
            'metric_landmarks': metric_landmarks,
        }
        #model_points = metric_landmarks[0:3, points_idx].T
        #image_points = landmarks[0:2, points_idx].T * np.array([frame_width, frame_height])[None, :]
        #success, rotation_vector, translation_vector = cv2.solvePnP(
        #    model_points,
        #    image_points,
        #    camera_matrix,
        #    dist_coeff,
        #    flags=cv2.SOLVEPNP_ITERATIVE
        #)

        #if success:
        #    return {
        #        'landmark': landmarks.T,
        #        'iris': iris_landmarks ,
        #        'rotation': rotation_vector,
        #        'translation': translation_vector,
        #        'metric_landmarks': metric_landmarks,
        #        'pose_transform_mat': pose_transform_mat
        #    }
        #return 45


    def capture(show_cam = False):
        with mp_face_mesh.FaceMesh(
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as face_mesh:

            if cap.isOpened():
                success, image = cap.read()
                if not success:
                    raise RuntimeError("Falha ao iniciar câmera")

                image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)

                image.flags.writeable = False
                results = face_mesh.process(image)

                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                LEFT_IRIS = [473, 474,475, 476, 477]
                RIGHT_IRIS = [468, 469, 470, 471, 472]
                img_h, img_w = image.shape[:2]
                faces = []
                close = False

                if results.multi_face_landmarks:

                    faces = list(map(getRigidInfo, results.multi_face_landmarks))

                    if show_cam:
                        for face_landmarks in results.multi_face_landmarks:
                            # image = cv2.blur(image, (30, 30))
                            mp_drawing.draw_landmarks(
                                image=image,
                                landmark_list=face_landmarks,
                                #connections=mp_face_mesh.FACE_CONNECTIONS,
                                connections=mp_face_mesh.FACEMESH_CONTOURS,
                                landmark_drawing_spec=drawing_spec,
                                connection_drawing_spec=drawing_spec
                            )
                            mesh_points = np.array([np.multiply([p.x, p.y], [img_w, img_h]).astype(int) for p in face_landmarks.landmark])
                            cv2.polylines(image, [mesh_points[LEFT_IRIS]], True, (0,255,0), 1, cv2.LINE_AA)
                            cv2.polylines(image, [mesh_points[RIGHT_IRIS]], True, (0,255,0), 1, cv2.LINE_AA)

                        cv2.namedWindow("Face", cv2.WINDOW_NORMAL)
                        # cv2.resizeWindow("Face", 800, 600)
                        cv2.imshow('Face', image)
                        if cv2.waitKey(1) & 0xFF == 27:
                            close = True
                    else:
                        cv2.destroyAllWindows()

                # Retorno das faces econtradas e do sinal de parada caso
                # janela de exibição seja fechada
                return faces, close

        raise RuntimeError("Falha ao iniciar câmera")

    def endCapture():
        cap.release()
        cv2.destroyAllWindows()

    return capture, endCapture

