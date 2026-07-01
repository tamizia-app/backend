--
-- PostgreSQL database dump
--

\restrict oUyxZXqoRsxlpW1IteYjg8RuSWR2EjefA3ZUkbPOXX26uj3exdoXTFmE08tWhnt

-- Dumped from database version 16.14
-- Dumped by pg_dump version 16.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: exercisetype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.exercisetype AS ENUM (
    'writing',
    'reading',
    'combined'
);


--
-- Name: riskflag; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.riskflag AS ENUM (
    'LOW',
    'MEDIUM',
    'HIGH_REVIEW'
);


--
-- Name: sessionstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.sessionstatus AS ENUM (
    'pending',
    'in_progress',
    'completed',
    'failed',
    'cancelled'
);


--
-- Name: userrole; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.userrole AS ENUM (
    'teacher',
    'admin'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: assessment_attempts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_attempts (
    id uuid NOT NULL,
    assessment_id uuid NOT NULL,
    student_id uuid NOT NULL,
    status character varying(20) DEFAULT 'IN_PROGRESS'::character varying NOT NULL,
    started_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    repeated_from_attempt_id uuid,
    repeat_reason text
);


--
-- Name: assessment_exercise_attempts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_exercise_attempts (
    id uuid NOT NULL,
    assessment_attempt_id uuid NOT NULL,
    template_exercise_id uuid NOT NULL,
    status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    started_at timestamp with time zone,
    submitted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: assessment_exercises; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_exercises (
    id uuid NOT NULL,
    type character varying(50) NOT NULL,
    title character varying(255) NOT NULL,
    instructions character varying(1000),
    stimulus_type character varying(50),
    response_type character varying(50),
    difficulty_level integer,
    is_active boolean DEFAULT true NOT NULL,
    created_by_teacher_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: assessment_expected_answers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_expected_answers (
    id uuid NOT NULL,
    prompt_exercise_id uuid NOT NULL,
    expected_text character varying(1000) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: assessment_mc_answer_options; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_mc_answer_options (
    id uuid NOT NULL,
    mc_question_id uuid NOT NULL,
    text character varying(255) NOT NULL,
    is_correct boolean DEFAULT false NOT NULL,
    order_index integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: assessment_mc_questions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_mc_questions (
    id uuid NOT NULL,
    exercise_id uuid NOT NULL,
    question_text character varying(500) NOT NULL,
    image_blob_path character varying(500),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: assessment_mc_responses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_mc_responses (
    id uuid NOT NULL,
    exercise_attempt_id uuid NOT NULL,
    selected_option_id uuid NOT NULL,
    is_correct boolean,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: assessment_os_answers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_os_answers (
    id uuid NOT NULL,
    os_question_id uuid NOT NULL,
    correct_word character varying(255) NOT NULL,
    syllables_json json NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: assessment_os_questions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_os_questions (
    id uuid NOT NULL,
    exercise_id uuid NOT NULL,
    question_text character varying(500) NOT NULL,
    image_blob_path character varying(500),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: assessment_os_responses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_os_responses (
    id uuid NOT NULL,
    exercise_attempt_id uuid NOT NULL,
    selected_syllables_json json NOT NULL,
    formed_word character varying(255),
    is_correct boolean,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: assessment_prompt_exercises; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_prompt_exercises (
    id uuid NOT NULL,
    exercise_id uuid NOT NULL,
    prompt_text character varying(1000),
    text_to_show character varying(500),
    audio_blob_path character varying(500),
    image_blob_path character varying(500),
    language_code character varying(20) DEFAULT 'es-PE'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: assessment_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_results (
    id uuid NOT NULL,
    assessment_attempt_id uuid NOT NULL,
    final_score double precision,
    max_score double precision,
    mc_correct_count integer,
    os_correct_count integer,
    speaking_completed_count integer,
    writing_completed_count integer,
    intervention_level character varying(20),
    generated_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: assessment_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_sessions (
    id uuid NOT NULL,
    student_id uuid NOT NULL,
    exercise_id uuid NOT NULL,
    teacher_profile_id uuid NOT NULL,
    status public.sessionstatus DEFAULT 'pending'::public.sessionstatus NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    duration_seconds integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: assessment_speaking_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_speaking_metrics (
    id uuid NOT NULL,
    speaking_response_id uuid NOT NULL,
    pronunciation_score double precision,
    accuracy_score double precision,
    fluency_score double precision,
    completeness_score double precision,
    prosody_score double precision,
    raw_speech_result_json json,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    raw_transcription_result_json json
);


--
-- Name: assessment_speaking_responses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_speaking_responses (
    id uuid NOT NULL,
    exercise_attempt_id uuid NOT NULL,
    audio_blob_path character varying(500) NOT NULL,
    original_filename character varying(255),
    content_type character varying(100),
    duration_ms integer,
    recognized_text character varying(2000),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    free_transcription_text character varying(2000),
    assessment_recognized_text character varying(2000)
);


--
-- Name: assessment_template_exercises; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_template_exercises (
    id uuid NOT NULL,
    template_id uuid NOT NULL,
    exercise_id uuid NOT NULL,
    order_index integer NOT NULL,
    points integer DEFAULT 10 NOT NULL,
    is_required boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: assessment_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_templates (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description character varying(500),
    version integer DEFAULT 1 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_by_teacher_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: assessment_writing_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_writing_metrics (
    id uuid NOT NULL,
    writing_response_id uuid NOT NULL,
    confidence_avg double precision,
    cer double precision,
    wer double precision,
    similarity_score double precision,
    raw_ocr_result_json json,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    duration_ms integer,
    stroke_count integer,
    point_count integer,
    average_speed double precision,
    speed_variability double precision,
    pause_count integer,
    longest_pause_ms integer,
    total_pause_time_ms integer,
    pressure_min double precision,
    pressure_max double precision,
    pressure_avg double precision,
    bounding_box_json json,
    writing_area_usage double precision
);


--
-- Name: assessment_writing_responses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_writing_responses (
    id uuid NOT NULL,
    exercise_attempt_id uuid NOT NULL,
    image_blob_path character varying(500) NOT NULL,
    original_filename character varying(255),
    content_type character varying(100),
    recognized_text character varying(2000),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    strokes_json json,
    canvas_metadata_json json,
    input_metadata_json json,
    frontend_metrics_json json
);


--
-- Name: assessments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessments (
    id uuid NOT NULL,
    template_id uuid NOT NULL,
    classroom_id uuid NOT NULL,
    homeroom_teacher_id uuid NOT NULL,
    title character varying(255),
    status character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    scheduled_at date,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: audio_samples; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audio_samples (
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    audio_url character varying(500) NOT NULL,
    duration_seconds integer,
    locale character varying(20) DEFAULT 'es-CO'::character varying NOT NULL,
    captured_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id uuid NOT NULL,
    user_id uuid,
    action character varying(100) NOT NULL,
    entity_type character varying(100) NOT NULL,
    entity_id character varying(36),
    metadata json,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: classrooms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.classrooms (
    id uuid NOT NULL,
    teacher_profile_id uuid NOT NULL,
    name character varying(120) NOT NULL,
    grade_level character varying(50) NOT NULL,
    section character varying(50),
    school_year character varying(20) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: exercises; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exercises (
    id uuid NOT NULL,
    type public.exercisetype NOT NULL,
    title character varying(255) NOT NULL,
    instructions text NOT NULL,
    reference_text text NOT NULL,
    difficulty_level integer NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: ocr_analyses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ocr_analyses (
    id uuid NOT NULL,
    writing_sample_id uuid NOT NULL,
    extracted_text text DEFAULT ''::text NOT NULL,
    confidence_avg double precision,
    cer_score double precision,
    wer_score double precision,
    omissions integer,
    substitutions integer,
    raw_response json,
    analyzed_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: password_reset_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.password_reset_tokens (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_hash character varying(255) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: pronunciation_analyses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pronunciation_analyses (
    id uuid NOT NULL,
    audio_sample_id uuid NOT NULL,
    accuracy_score double precision,
    fluency_score double precision,
    completeness_score double precision,
    pronunciation_score double precision,
    recognized_text text,
    raw_response json,
    analyzed_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: refresh_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.refresh_tokens (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_hash character varying(255) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    revoked_at timestamp with time zone
);


--
-- Name: refresh_tokens_iam; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.refresh_tokens_iam (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_hash character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    revoked_at timestamp with time zone
);


--
-- Name: school_classrooms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.school_classrooms (
    id uuid NOT NULL,
    homeroom_teacher_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    grade_level character varying(20) NOT NULL,
    section character varying(1) NOT NULL,
    school_year date NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: session_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_results (
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    writing_score double precision,
    reading_score double precision,
    overall_score double precision,
    observation text NOT NULL,
    risk_flag public.riskflag NOT NULL,
    generated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: student_consents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_consents (
    id uuid NOT NULL,
    student_id uuid NOT NULL,
    status boolean DEFAULT false NOT NULL,
    consent_date timestamp with time zone,
    revoked_at timestamp with time zone,
    evidence_blob_path character varying(500),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: students; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.students (
    id uuid NOT NULL,
    classroom_id uuid NOT NULL,
    code character varying(50) NOT NULL,
    age integer NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    gender character varying(10) DEFAULT 'BOY'::character varying NOT NULL
);


--
-- Name: teacher_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teacher_profiles (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    institution_name character varying(255),
    phone character varying(50),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: teachers_iam; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teachers_iam (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    institute_name character varying(255),
    phone character varying(50),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    full_name character varying(255) NOT NULL,
    role public.userrole NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: users_iam; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users_iam (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    lastname character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: writing_samples; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.writing_samples (
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    image_url character varying(500) NOT NULL,
    source_type character varying(50) NOT NULL,
    stroke_count integer,
    correction_count integer,
    duration_seconds integer,
    captured_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: assessment_attempts pk_assessment_attempts; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_attempts
    ADD CONSTRAINT pk_assessment_attempts PRIMARY KEY (id);


--
-- Name: assessment_exercise_attempts pk_assessment_exercise_attempts; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_exercise_attempts
    ADD CONSTRAINT pk_assessment_exercise_attempts PRIMARY KEY (id);


--
-- Name: assessment_exercises pk_assessment_exercises; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_exercises
    ADD CONSTRAINT pk_assessment_exercises PRIMARY KEY (id);


--
-- Name: assessment_expected_answers pk_assessment_expected_answers; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_expected_answers
    ADD CONSTRAINT pk_assessment_expected_answers PRIMARY KEY (id);


--
-- Name: assessment_mc_answer_options pk_assessment_mc_answer_options; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_mc_answer_options
    ADD CONSTRAINT pk_assessment_mc_answer_options PRIMARY KEY (id);


--
-- Name: assessment_mc_questions pk_assessment_mc_questions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_mc_questions
    ADD CONSTRAINT pk_assessment_mc_questions PRIMARY KEY (id);


--
-- Name: assessment_mc_responses pk_assessment_mc_responses; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_mc_responses
    ADD CONSTRAINT pk_assessment_mc_responses PRIMARY KEY (id);


--
-- Name: assessment_os_answers pk_assessment_os_answers; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_os_answers
    ADD CONSTRAINT pk_assessment_os_answers PRIMARY KEY (id);


--
-- Name: assessment_os_questions pk_assessment_os_questions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_os_questions
    ADD CONSTRAINT pk_assessment_os_questions PRIMARY KEY (id);


--
-- Name: assessment_os_responses pk_assessment_os_responses; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_os_responses
    ADD CONSTRAINT pk_assessment_os_responses PRIMARY KEY (id);


--
-- Name: assessment_prompt_exercises pk_assessment_prompt_exercises; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_prompt_exercises
    ADD CONSTRAINT pk_assessment_prompt_exercises PRIMARY KEY (id);


--
-- Name: assessment_results pk_assessment_results; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_results
    ADD CONSTRAINT pk_assessment_results PRIMARY KEY (id);


--
-- Name: assessment_sessions pk_assessment_sessions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_sessions
    ADD CONSTRAINT pk_assessment_sessions PRIMARY KEY (id);


--
-- Name: assessment_speaking_metrics pk_assessment_speaking_metrics; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_speaking_metrics
    ADD CONSTRAINT pk_assessment_speaking_metrics PRIMARY KEY (id);


--
-- Name: assessment_speaking_responses pk_assessment_speaking_responses; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_speaking_responses
    ADD CONSTRAINT pk_assessment_speaking_responses PRIMARY KEY (id);


--
-- Name: assessment_template_exercises pk_assessment_template_exercises; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_template_exercises
    ADD CONSTRAINT pk_assessment_template_exercises PRIMARY KEY (id);


--
-- Name: assessment_templates pk_assessment_templates; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_templates
    ADD CONSTRAINT pk_assessment_templates PRIMARY KEY (id);


--
-- Name: assessment_writing_metrics pk_assessment_writing_metrics; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_writing_metrics
    ADD CONSTRAINT pk_assessment_writing_metrics PRIMARY KEY (id);


--
-- Name: assessment_writing_responses pk_assessment_writing_responses; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_writing_responses
    ADD CONSTRAINT pk_assessment_writing_responses PRIMARY KEY (id);


--
-- Name: assessments pk_assessments; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessments
    ADD CONSTRAINT pk_assessments PRIMARY KEY (id);


--
-- Name: audio_samples pk_audio_samples; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audio_samples
    ADD CONSTRAINT pk_audio_samples PRIMARY KEY (id);


--
-- Name: audit_logs pk_audit_logs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT pk_audit_logs PRIMARY KEY (id);


--
-- Name: classrooms pk_classrooms; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.classrooms
    ADD CONSTRAINT pk_classrooms PRIMARY KEY (id);


--
-- Name: exercises pk_exercises; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exercises
    ADD CONSTRAINT pk_exercises PRIMARY KEY (id);


--
-- Name: ocr_analyses pk_ocr_analyses; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocr_analyses
    ADD CONSTRAINT pk_ocr_analyses PRIMARY KEY (id);


--
-- Name: password_reset_tokens pk_password_reset_tokens; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT pk_password_reset_tokens PRIMARY KEY (id);


--
-- Name: pronunciation_analyses pk_pronunciation_analyses; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pronunciation_analyses
    ADD CONSTRAINT pk_pronunciation_analyses PRIMARY KEY (id);


--
-- Name: refresh_tokens pk_refresh_tokens; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT pk_refresh_tokens PRIMARY KEY (id);


--
-- Name: refresh_tokens_iam pk_refresh_tokens_iam; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens_iam
    ADD CONSTRAINT pk_refresh_tokens_iam PRIMARY KEY (id);


--
-- Name: school_classrooms pk_school_classrooms; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.school_classrooms
    ADD CONSTRAINT pk_school_classrooms PRIMARY KEY (id);


--
-- Name: session_results pk_session_results; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_results
    ADD CONSTRAINT pk_session_results PRIMARY KEY (id);


--
-- Name: student_consents pk_student_consents; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_consents
    ADD CONSTRAINT pk_student_consents PRIMARY KEY (id);


--
-- Name: students pk_students; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.students
    ADD CONSTRAINT pk_students PRIMARY KEY (id);


--
-- Name: teacher_profiles pk_teacher_profiles; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_profiles
    ADD CONSTRAINT pk_teacher_profiles PRIMARY KEY (id);


--
-- Name: teachers_iam pk_teachers_iam; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teachers_iam
    ADD CONSTRAINT pk_teachers_iam PRIMARY KEY (id);


--
-- Name: users pk_users; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT pk_users PRIMARY KEY (id);


--
-- Name: users_iam pk_users_iam; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_iam
    ADD CONSTRAINT pk_users_iam PRIMARY KEY (id);


--
-- Name: writing_samples pk_writing_samples; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.writing_samples
    ADD CONSTRAINT pk_writing_samples PRIMARY KEY (id);


--
-- Name: assessment_expected_answers uq_assessment_expected_answers_prompt_exercise_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_expected_answers
    ADD CONSTRAINT uq_assessment_expected_answers_prompt_exercise_id UNIQUE (prompt_exercise_id);


--
-- Name: assessment_mc_questions uq_assessment_mc_questions_exercise_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_mc_questions
    ADD CONSTRAINT uq_assessment_mc_questions_exercise_id UNIQUE (exercise_id);


--
-- Name: assessment_mc_responses uq_assessment_mc_responses_exercise_attempt_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_mc_responses
    ADD CONSTRAINT uq_assessment_mc_responses_exercise_attempt_id UNIQUE (exercise_attempt_id);


--
-- Name: assessment_os_answers uq_assessment_os_answers_os_question_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_os_answers
    ADD CONSTRAINT uq_assessment_os_answers_os_question_id UNIQUE (os_question_id);


--
-- Name: assessment_os_questions uq_assessment_os_questions_exercise_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_os_questions
    ADD CONSTRAINT uq_assessment_os_questions_exercise_id UNIQUE (exercise_id);


--
-- Name: assessment_os_responses uq_assessment_os_responses_exercise_attempt_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_os_responses
    ADD CONSTRAINT uq_assessment_os_responses_exercise_attempt_id UNIQUE (exercise_attempt_id);


--
-- Name: assessment_prompt_exercises uq_assessment_prompt_exercises_exercise_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_prompt_exercises
    ADD CONSTRAINT uq_assessment_prompt_exercises_exercise_id UNIQUE (exercise_id);


--
-- Name: assessment_results uq_assessment_results_assessment_attempt_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_results
    ADD CONSTRAINT uq_assessment_results_assessment_attempt_id UNIQUE (assessment_attempt_id);


--
-- Name: assessment_speaking_metrics uq_assessment_speaking_metrics_speaking_response_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_speaking_metrics
    ADD CONSTRAINT uq_assessment_speaking_metrics_speaking_response_id UNIQUE (speaking_response_id);


--
-- Name: assessment_speaking_responses uq_assessment_speaking_responses_exercise_attempt_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_speaking_responses
    ADD CONSTRAINT uq_assessment_speaking_responses_exercise_attempt_id UNIQUE (exercise_attempt_id);


--
-- Name: assessment_writing_metrics uq_assessment_writing_metrics_writing_response_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_writing_metrics
    ADD CONSTRAINT uq_assessment_writing_metrics_writing_response_id UNIQUE (writing_response_id);


--
-- Name: assessment_writing_responses uq_assessment_writing_responses_exercise_attempt_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_writing_responses
    ADD CONSTRAINT uq_assessment_writing_responses_exercise_attempt_id UNIQUE (exercise_attempt_id);


--
-- Name: audio_samples uq_audio_samples_session_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audio_samples
    ADD CONSTRAINT uq_audio_samples_session_id UNIQUE (session_id);


--
-- Name: ocr_analyses uq_ocr_analyses_writing_sample_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocr_analyses
    ADD CONSTRAINT uq_ocr_analyses_writing_sample_id UNIQUE (writing_sample_id);


--
-- Name: password_reset_tokens uq_password_reset_tokens_token_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT uq_password_reset_tokens_token_hash UNIQUE (token_hash);


--
-- Name: pronunciation_analyses uq_pronunciation_analyses_audio_sample_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pronunciation_analyses
    ADD CONSTRAINT uq_pronunciation_analyses_audio_sample_id UNIQUE (audio_sample_id);


--
-- Name: refresh_tokens_iam uq_refresh_tokens_iam_token_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens_iam
    ADD CONSTRAINT uq_refresh_tokens_iam_token_hash UNIQUE (token_hash);


--
-- Name: refresh_tokens uq_refresh_tokens_token_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT uq_refresh_tokens_token_hash UNIQUE (token_hash);


--
-- Name: session_results uq_session_results_session_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_results
    ADD CONSTRAINT uq_session_results_session_id UNIQUE (session_id);


--
-- Name: student_consents uq_student_consents_student_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_consents
    ADD CONSTRAINT uq_student_consents_student_id UNIQUE (student_id);


--
-- Name: students uq_students_classroom_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.students
    ADD CONSTRAINT uq_students_classroom_code UNIQUE (classroom_id, code);


--
-- Name: teacher_profiles uq_teacher_profiles_user_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_profiles
    ADD CONSTRAINT uq_teacher_profiles_user_id UNIQUE (user_id);


--
-- Name: teachers_iam uq_teachers_iam_phone; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teachers_iam
    ADD CONSTRAINT uq_teachers_iam_phone UNIQUE (phone);


--
-- Name: teachers_iam uq_teachers_iam_user_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teachers_iam
    ADD CONSTRAINT uq_teachers_iam_user_id UNIQUE (user_id);


--
-- Name: users uq_users_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_email UNIQUE (email);


--
-- Name: users_iam uq_users_iam_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_iam
    ADD CONSTRAINT uq_users_iam_email UNIQUE (email);


--
-- Name: writing_samples uq_writing_samples_session_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.writing_samples
    ADD CONSTRAINT uq_writing_samples_session_id UNIQUE (session_id);


--
-- Name: ix_assessment_attempts_assessment_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessment_attempts_assessment_id ON public.assessment_attempts USING btree (assessment_id);


--
-- Name: ix_assessment_attempts_repeated_from_attempt_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessment_attempts_repeated_from_attempt_id ON public.assessment_attempts USING btree (repeated_from_attempt_id);


--
-- Name: ix_assessment_attempts_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessment_attempts_student_id ON public.assessment_attempts USING btree (student_id);


--
-- Name: ix_assessment_exercise_attempts_assessment_attempt_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessment_exercise_attempts_assessment_attempt_id ON public.assessment_exercise_attempts USING btree (assessment_attempt_id);


--
-- Name: ix_assessment_exercise_attempts_template_exercise_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessment_exercise_attempts_template_exercise_id ON public.assessment_exercise_attempts USING btree (template_exercise_id);


--
-- Name: ix_assessment_exercises_created_by_teacher_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessment_exercises_created_by_teacher_id ON public.assessment_exercises USING btree (created_by_teacher_id);


--
-- Name: ix_assessment_exercises_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessment_exercises_type ON public.assessment_exercises USING btree (type);


--
-- Name: ix_assessment_expected_answers_prompt_exercise_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_assessment_expected_answers_prompt_exercise_id ON public.assessment_expected_answers USING btree (prompt_exercise_id);


--
-- Name: ix_assessment_mc_answer_options_mc_question_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessment_mc_answer_options_mc_question_id ON public.assessment_mc_answer_options USING btree (mc_question_id);


--
-- Name: ix_assessment_mc_questions_exercise_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_assessment_mc_questions_exercise_id ON public.assessment_mc_questions USING btree (exercise_id);


--
-- Name: ix_assessment_mc_responses_exercise_attempt_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_assessment_mc_responses_exercise_attempt_id ON public.assessment_mc_responses USING btree (exercise_attempt_id);


--
-- Name: ix_assessment_os_answers_os_question_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_assessment_os_answers_os_question_id ON public.assessment_os_answers USING btree (os_question_id);


--
-- Name: ix_assessment_os_questions_exercise_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_assessment_os_questions_exercise_id ON public.assessment_os_questions USING btree (exercise_id);


--
-- Name: ix_assessment_os_responses_exercise_attempt_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_assessment_os_responses_exercise_attempt_id ON public.assessment_os_responses USING btree (exercise_attempt_id);


--
-- Name: ix_assessment_prompt_exercises_exercise_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_assessment_prompt_exercises_exercise_id ON public.assessment_prompt_exercises USING btree (exercise_id);


--
-- Name: ix_assessment_results_assessment_attempt_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_assessment_results_assessment_attempt_id ON public.assessment_results USING btree (assessment_attempt_id);


--
-- Name: ix_assessment_sessions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessment_sessions_status ON public.assessment_sessions USING btree (status);


--
-- Name: ix_assessment_sessions_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessment_sessions_student_id ON public.assessment_sessions USING btree (student_id);


--
-- Name: ix_assessment_sessions_teacher_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessment_sessions_teacher_profile_id ON public.assessment_sessions USING btree (teacher_profile_id);


--
-- Name: ix_assessment_speaking_metrics_speaking_response_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_assessment_speaking_metrics_speaking_response_id ON public.assessment_speaking_metrics USING btree (speaking_response_id);


--
-- Name: ix_assessment_speaking_responses_exercise_attempt_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_assessment_speaking_responses_exercise_attempt_id ON public.assessment_speaking_responses USING btree (exercise_attempt_id);


--
-- Name: ix_assessment_template_exercises_exercise_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessment_template_exercises_exercise_id ON public.assessment_template_exercises USING btree (exercise_id);


--
-- Name: ix_assessment_template_exercises_template_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessment_template_exercises_template_id ON public.assessment_template_exercises USING btree (template_id);


--
-- Name: ix_assessment_templates_created_by_teacher_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessment_templates_created_by_teacher_id ON public.assessment_templates USING btree (created_by_teacher_id);


--
-- Name: ix_assessment_writing_metrics_writing_response_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_assessment_writing_metrics_writing_response_id ON public.assessment_writing_metrics USING btree (writing_response_id);


--
-- Name: ix_assessment_writing_responses_exercise_attempt_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_assessment_writing_responses_exercise_attempt_id ON public.assessment_writing_responses USING btree (exercise_attempt_id);


--
-- Name: ix_assessments_classroom_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessments_classroom_id ON public.assessments USING btree (classroom_id);


--
-- Name: ix_assessments_homeroom_teacher_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessments_homeroom_teacher_id ON public.assessments USING btree (homeroom_teacher_id);


--
-- Name: ix_assessments_template_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assessments_template_id ON public.assessments USING btree (template_id);


--
-- Name: ix_audit_logs_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_user_id ON public.audit_logs USING btree (user_id);


--
-- Name: ix_classrooms_teacher_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_classrooms_teacher_profile_id ON public.classrooms USING btree (teacher_profile_id);


--
-- Name: ix_exercises_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_exercises_type ON public.exercises USING btree (type);


--
-- Name: ix_password_reset_tokens_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_password_reset_tokens_user_id ON public.password_reset_tokens USING btree (user_id);


--
-- Name: ix_refresh_tokens_iam_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_refresh_tokens_iam_user_id ON public.refresh_tokens_iam USING btree (user_id);


--
-- Name: ix_refresh_tokens_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_refresh_tokens_user_id ON public.refresh_tokens USING btree (user_id);


--
-- Name: ix_school_classrooms_homeroom_teacher_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_school_classrooms_homeroom_teacher_id ON public.school_classrooms USING btree (homeroom_teacher_id);


--
-- Name: ix_student_consents_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_student_consents_student_id ON public.student_consents USING btree (student_id);


--
-- Name: ix_students_classroom_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_students_classroom_id ON public.students USING btree (classroom_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_iam_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_iam_email ON public.users_iam USING btree (email);


--
-- Name: assessment_attempts fk_assessment_attempts_assessment_id_assessments; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_attempts
    ADD CONSTRAINT fk_assessment_attempts_assessment_id_assessments FOREIGN KEY (assessment_id) REFERENCES public.assessments(id) ON DELETE CASCADE;


--
-- Name: assessment_attempts fk_assessment_attempts_repeated_from_attempt_id_assessm_83d5; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_attempts
    ADD CONSTRAINT fk_assessment_attempts_repeated_from_attempt_id_assessm_83d5 FOREIGN KEY (repeated_from_attempt_id) REFERENCES public.assessment_attempts(id) ON DELETE SET NULL;


--
-- Name: assessment_attempts fk_assessment_attempts_student_id_students; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_attempts
    ADD CONSTRAINT fk_assessment_attempts_student_id_students FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE CASCADE;


--
-- Name: assessment_exercise_attempts fk_assessment_exercise_attempts_assessment_attempt_id_a_bbac; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_exercise_attempts
    ADD CONSTRAINT fk_assessment_exercise_attempts_assessment_attempt_id_a_bbac FOREIGN KEY (assessment_attempt_id) REFERENCES public.assessment_attempts(id) ON DELETE CASCADE;


--
-- Name: assessment_exercise_attempts fk_assessment_exercise_attempts_template_exercise_id_as_9c7e; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_exercise_attempts
    ADD CONSTRAINT fk_assessment_exercise_attempts_template_exercise_id_as_9c7e FOREIGN KEY (template_exercise_id) REFERENCES public.assessment_template_exercises(id) ON DELETE CASCADE;


--
-- Name: assessment_exercises fk_assessment_exercises_created_by_teacher_id_teachers_iam; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_exercises
    ADD CONSTRAINT fk_assessment_exercises_created_by_teacher_id_teachers_iam FOREIGN KEY (created_by_teacher_id) REFERENCES public.teachers_iam(id) ON DELETE SET NULL;


--
-- Name: assessment_expected_answers fk_assessment_expected_answers_prompt_exercise_id_asses_d7f2; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_expected_answers
    ADD CONSTRAINT fk_assessment_expected_answers_prompt_exercise_id_asses_d7f2 FOREIGN KEY (prompt_exercise_id) REFERENCES public.assessment_prompt_exercises(id) ON DELETE CASCADE;


--
-- Name: assessment_mc_answer_options fk_assessment_mc_answer_options_mc_question_id_assessme_509b; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_mc_answer_options
    ADD CONSTRAINT fk_assessment_mc_answer_options_mc_question_id_assessme_509b FOREIGN KEY (mc_question_id) REFERENCES public.assessment_mc_questions(id) ON DELETE CASCADE;


--
-- Name: assessment_mc_questions fk_assessment_mc_questions_exercise_id_assessment_exercises; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_mc_questions
    ADD CONSTRAINT fk_assessment_mc_questions_exercise_id_assessment_exercises FOREIGN KEY (exercise_id) REFERENCES public.assessment_exercises(id) ON DELETE CASCADE;


--
-- Name: assessment_mc_responses fk_assessment_mc_responses_exercise_attempt_id_assessme_ae58; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_mc_responses
    ADD CONSTRAINT fk_assessment_mc_responses_exercise_attempt_id_assessme_ae58 FOREIGN KEY (exercise_attempt_id) REFERENCES public.assessment_exercise_attempts(id) ON DELETE CASCADE;


--
-- Name: assessment_mc_responses fk_assessment_mc_responses_selected_option_id_assessmen_397b; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_mc_responses
    ADD CONSTRAINT fk_assessment_mc_responses_selected_option_id_assessmen_397b FOREIGN KEY (selected_option_id) REFERENCES public.assessment_mc_answer_options(id) ON DELETE CASCADE;


--
-- Name: assessment_os_answers fk_assessment_os_answers_os_question_id_assessment_os_questions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_os_answers
    ADD CONSTRAINT fk_assessment_os_answers_os_question_id_assessment_os_questions FOREIGN KEY (os_question_id) REFERENCES public.assessment_os_questions(id) ON DELETE CASCADE;


--
-- Name: assessment_os_questions fk_assessment_os_questions_exercise_id_assessment_exercises; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_os_questions
    ADD CONSTRAINT fk_assessment_os_questions_exercise_id_assessment_exercises FOREIGN KEY (exercise_id) REFERENCES public.assessment_exercises(id) ON DELETE CASCADE;


--
-- Name: assessment_os_responses fk_assessment_os_responses_exercise_attempt_id_assessme_c1ac; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_os_responses
    ADD CONSTRAINT fk_assessment_os_responses_exercise_attempt_id_assessme_c1ac FOREIGN KEY (exercise_attempt_id) REFERENCES public.assessment_exercise_attempts(id) ON DELETE CASCADE;


--
-- Name: assessment_prompt_exercises fk_assessment_prompt_exercises_exercise_id_assessment_exercises; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_prompt_exercises
    ADD CONSTRAINT fk_assessment_prompt_exercises_exercise_id_assessment_exercises FOREIGN KEY (exercise_id) REFERENCES public.assessment_exercises(id) ON DELETE CASCADE;


--
-- Name: assessment_results fk_assessment_results_assessment_attempt_id_assessment_attempts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_results
    ADD CONSTRAINT fk_assessment_results_assessment_attempt_id_assessment_attempts FOREIGN KEY (assessment_attempt_id) REFERENCES public.assessment_attempts(id) ON DELETE CASCADE;


--
-- Name: assessment_sessions fk_assessment_sessions_exercise_id_exercises; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_sessions
    ADD CONSTRAINT fk_assessment_sessions_exercise_id_exercises FOREIGN KEY (exercise_id) REFERENCES public.exercises(id);


--
-- Name: assessment_sessions fk_assessment_sessions_student_id_students; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_sessions
    ADD CONSTRAINT fk_assessment_sessions_student_id_students FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE CASCADE;


--
-- Name: assessment_sessions fk_assessment_sessions_teacher_profile_id_teacher_profiles; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_sessions
    ADD CONSTRAINT fk_assessment_sessions_teacher_profile_id_teacher_profiles FOREIGN KEY (teacher_profile_id) REFERENCES public.teacher_profiles(id) ON DELETE CASCADE;


--
-- Name: assessment_speaking_metrics fk_assessment_speaking_metrics_speaking_response_id_ass_cb1a; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_speaking_metrics
    ADD CONSTRAINT fk_assessment_speaking_metrics_speaking_response_id_ass_cb1a FOREIGN KEY (speaking_response_id) REFERENCES public.assessment_speaking_responses(id) ON DELETE CASCADE;


--
-- Name: assessment_speaking_responses fk_assessment_speaking_responses_exercise_attempt_id_as_8f5c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_speaking_responses
    ADD CONSTRAINT fk_assessment_speaking_responses_exercise_attempt_id_as_8f5c FOREIGN KEY (exercise_attempt_id) REFERENCES public.assessment_exercise_attempts(id) ON DELETE CASCADE;


--
-- Name: assessment_template_exercises fk_assessment_template_exercises_exercise_id_assessment_4c9c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_template_exercises
    ADD CONSTRAINT fk_assessment_template_exercises_exercise_id_assessment_4c9c FOREIGN KEY (exercise_id) REFERENCES public.assessment_exercises(id) ON DELETE CASCADE;


--
-- Name: assessment_template_exercises fk_assessment_template_exercises_template_id_assessment_ec1a; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_template_exercises
    ADD CONSTRAINT fk_assessment_template_exercises_template_id_assessment_ec1a FOREIGN KEY (template_id) REFERENCES public.assessment_templates(id) ON DELETE CASCADE;


--
-- Name: assessment_templates fk_assessment_templates_created_by_teacher_id_teachers_iam; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_templates
    ADD CONSTRAINT fk_assessment_templates_created_by_teacher_id_teachers_iam FOREIGN KEY (created_by_teacher_id) REFERENCES public.teachers_iam(id) ON DELETE SET NULL;


--
-- Name: assessment_writing_metrics fk_assessment_writing_metrics_writing_response_id_asses_de6d; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_writing_metrics
    ADD CONSTRAINT fk_assessment_writing_metrics_writing_response_id_asses_de6d FOREIGN KEY (writing_response_id) REFERENCES public.assessment_writing_responses(id) ON DELETE CASCADE;


--
-- Name: assessment_writing_responses fk_assessment_writing_responses_exercise_attempt_id_ass_47ee; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_writing_responses
    ADD CONSTRAINT fk_assessment_writing_responses_exercise_attempt_id_ass_47ee FOREIGN KEY (exercise_attempt_id) REFERENCES public.assessment_exercise_attempts(id) ON DELETE CASCADE;


--
-- Name: assessments fk_assessments_classroom_id_school_classrooms; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessments
    ADD CONSTRAINT fk_assessments_classroom_id_school_classrooms FOREIGN KEY (classroom_id) REFERENCES public.school_classrooms(id) ON DELETE CASCADE;


--
-- Name: assessments fk_assessments_homeroom_teacher_id_teachers_iam; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessments
    ADD CONSTRAINT fk_assessments_homeroom_teacher_id_teachers_iam FOREIGN KEY (homeroom_teacher_id) REFERENCES public.teachers_iam(id) ON DELETE CASCADE;


--
-- Name: assessments fk_assessments_template_id_assessment_templates; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessments
    ADD CONSTRAINT fk_assessments_template_id_assessment_templates FOREIGN KEY (template_id) REFERENCES public.assessment_templates(id) ON DELETE CASCADE;


--
-- Name: audio_samples fk_audio_samples_session_id_assessment_sessions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audio_samples
    ADD CONSTRAINT fk_audio_samples_session_id_assessment_sessions FOREIGN KEY (session_id) REFERENCES public.assessment_sessions(id) ON DELETE CASCADE;


--
-- Name: audit_logs fk_audit_logs_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT fk_audit_logs_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: classrooms fk_classrooms_teacher_profile_id_teacher_profiles; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.classrooms
    ADD CONSTRAINT fk_classrooms_teacher_profile_id_teacher_profiles FOREIGN KEY (teacher_profile_id) REFERENCES public.teacher_profiles(id) ON DELETE CASCADE;


--
-- Name: ocr_analyses fk_ocr_analyses_writing_sample_id_writing_samples; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocr_analyses
    ADD CONSTRAINT fk_ocr_analyses_writing_sample_id_writing_samples FOREIGN KEY (writing_sample_id) REFERENCES public.writing_samples(id) ON DELETE CASCADE;


--
-- Name: password_reset_tokens fk_password_reset_tokens_user_id_users_iam; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT fk_password_reset_tokens_user_id_users_iam FOREIGN KEY (user_id) REFERENCES public.users_iam(id) ON DELETE CASCADE;


--
-- Name: pronunciation_analyses fk_pronunciation_analyses_audio_sample_id_audio_samples; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pronunciation_analyses
    ADD CONSTRAINT fk_pronunciation_analyses_audio_sample_id_audio_samples FOREIGN KEY (audio_sample_id) REFERENCES public.audio_samples(id) ON DELETE CASCADE;


--
-- Name: refresh_tokens_iam fk_refresh_tokens_iam_user_id_users_iam; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens_iam
    ADD CONSTRAINT fk_refresh_tokens_iam_user_id_users_iam FOREIGN KEY (user_id) REFERENCES public.users_iam(id) ON DELETE CASCADE;


--
-- Name: refresh_tokens fk_refresh_tokens_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT fk_refresh_tokens_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: school_classrooms fk_school_classrooms_homeroom_teacher_id_teachers_iam; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.school_classrooms
    ADD CONSTRAINT fk_school_classrooms_homeroom_teacher_id_teachers_iam FOREIGN KEY (homeroom_teacher_id) REFERENCES public.teachers_iam(id) ON DELETE CASCADE;


--
-- Name: session_results fk_session_results_session_id_assessment_sessions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_results
    ADD CONSTRAINT fk_session_results_session_id_assessment_sessions FOREIGN KEY (session_id) REFERENCES public.assessment_sessions(id) ON DELETE CASCADE;


--
-- Name: student_consents fk_student_consents_student_id_students; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_consents
    ADD CONSTRAINT fk_student_consents_student_id_students FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE CASCADE;


--
-- Name: students fk_students_classroom_id_school_classrooms; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.students
    ADD CONSTRAINT fk_students_classroom_id_school_classrooms FOREIGN KEY (classroom_id) REFERENCES public.school_classrooms(id) ON DELETE CASCADE;


--
-- Name: teacher_profiles fk_teacher_profiles_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_profiles
    ADD CONSTRAINT fk_teacher_profiles_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: teachers_iam fk_teachers_iam_user_id_users_iam; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teachers_iam
    ADD CONSTRAINT fk_teachers_iam_user_id_users_iam FOREIGN KEY (user_id) REFERENCES public.users_iam(id) ON DELETE CASCADE;


--
-- Name: writing_samples fk_writing_samples_session_id_assessment_sessions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.writing_samples
    ADD CONSTRAINT fk_writing_samples_session_id_assessment_sessions FOREIGN KEY (session_id) REFERENCES public.assessment_sessions(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict oUyxZXqoRsxlpW1IteYjg8RuSWR2EjefA3ZUkbPOXX26uj3exdoXTFmE08tWhnt

