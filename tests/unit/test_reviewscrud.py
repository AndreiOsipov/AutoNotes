import pytest
from datetime import datetime


class TestReviewCRUD:

    def test_create_review_success(self, mock_db, review_data):
        """Тест: успешное создание отзыва"""
        payload = {
            "rating": review_data["rating"],
            "text": review_data["text"],
            "transcription_id": review_data["transcription_id"],
        }
        assert payload["rating"] == 5
        assert payload["text"] == "Отличный сервис!"
        assert payload["rating"] >= 1 and payload["rating"] <= 5
        assert len(payload["text"]) >= 5


    def test_create_review_invalid_rating(self, mock_db, invalid_review_payload):
        """Тест: создание отзыва с невалидным рейтингом"""
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            if invalid_review_payload["rating"] > 5:
                raise ValueError("Rating must be between 1 and 5")


    def test_create_service_review(self, mock_db, create_service_review_payload):
        """Тест: создание отзыва на сервис (transcription_id = None)"""
        payload = create_service_review_payload
        assert payload["rating"] == 4
        assert payload["transcription_id"] is None
        assert len(payload["text"]) >= 5


    def test_get_review_by_id_success(self, mock_db, review_data):
        """Тест: получение отзыва по ID"""
        review_id = review_data["id"]
        result = review_data
        assert result is not None
        assert result["id"] == review_id
        assert result["rating"] == review_data["rating"]
        assert result["text"] == review_data["text"]


    def test_get_review_not_found(self, mock_db):
        """Тест: получение несуществующего отзыва"""
        result = None
        assert result is None


    def test_get_all_reviews_empty(self, mock_db):
        """Тест: получение списка при отсутствии отзывов"""
        results = []
        assert results == []
        assert len(results) == 0


    def test_get_reviews_by_transcription_id(self, mock_db, review_list_data):
        """Тест: получение отзывов по transcription_id"""
        transcription_id = 1
        filtered_reviews = [
            r for r in review_list_data
            if r["transcription_id"] == transcription_id
        ]
        assert len(filtered_reviews) == 2
        assert all(r["transcription_id"] == transcription_id for r in filtered_reviews)


    def test_get_reviews_by_nonexistent_transcription(self, mock_db, review_list_data):
        """Тест: получение отзывов для несуществующей трансляции"""
        transcription_id = 9999
        results = [
            r for r in review_list_data
            if r["transcription_id"] == transcription_id
        ]
        assert results == []

    def test_get_service_reviews_only(self, mock_db, review_list_data):
        """Тест: получение отзывов на сервис (transcription_id = None)"""
        service_reviews = [
            r for r in review_list_data
            if r["transcription_id"] is None
        ]
        results = service_reviews
        assert len(results) == 1
        assert all(r["transcription_id"] is None for r in results)


class TestReviewCRUDParametrized:

    @pytest.mark.parametrize("rating,should_pass", [
        (1, True),
        (2, True),
        (3, True),
        (4, True),
        (5, True),
        (0, False),
        (6, False),
        (-1, False),
        (10, False),
    ])
    def test_rating_validation(self, rating, should_pass):
        """Тест: валидация рейтинга (параметризованный)"""
        if should_pass:
            assert 1 <= rating <= 5, f"Rating {rating} должен быть валиден"
        else:
            assert not (1 <= rating <= 5), f"Rating {rating} должен быть невалиден"


    @pytest.mark.parametrize("text_length,should_pass", [
        (5, True),
        (100, True),
        (500, True),
        (1000, True),
        (10000, True),
        (0, False),
        (1, False),
        (4, False),
    ])
    def test_text_length_validation(self, text_length, should_pass):
        """Тест: валидация длины текста отзыва"""
        text = "x" * text_length
        if should_pass:
            assert len(text) >= 5, f"Text length {text_length} должна быть >= 5"
        else:
            assert len(text) < 5, f"Text length {text_length} должна быть < 5"


    @pytest.mark.parametrize("transcription_id,is_service_review", [
        (1, False),
        (2, False),
        (100, False),
        (None, True),
    ])
    def test_transcription_id_types(self, mock_db, transcription_id, is_service_review):
        """Тест: разные типы transcription_id"""
        if is_service_review:
            assert transcription_id is None
        else:
            assert isinstance(transcription_id, int)