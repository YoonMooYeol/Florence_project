  async function addBabyDiaryPhoto(diaryId, photoFile) {
    isLoading.value = true
    error.value = null
    
    try {
      console.log(`태교일기 사진 업로드 시작 - diary_id: ${diaryId}, 파일 이름: ${photoFile.name}`)
      console.log(`파일 타입: ${photoFile.type}, 파일 크기: ${photoFile.size} bytes`)
      
      // FormData 객체 생성 및 파일 추가
      const formData = new FormData()
      formData.append('image', photoFile)
      
      // 디버깅 정보
      for (let [key, value] of formData.entries()) {
        if (value instanceof File) {
          console.log(`FormData: ${key} = File(${value.name}, ${value.type}, ${value.size} bytes)`)
        } else {
          console.log(`FormData: ${key} = ${value}`)
        }
      }
      
      // 설정 객체 - 멀티파트 폼데이터 요청 (헤더 추가)
      const config = {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        // 업로드 진행상황 트래킹 (옵션)
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          console.log(`업로드 진행률: ${percentCompleted}%`)
        }
      }
      
      // API 호출 로그
      console.log(`API 호출: POST calendars/baby-diaries/${diaryId}/photo/`)
      
      // API 호출
      const response = await api.post(`calendars/baby-diaries/${diaryId}/photo/`, formData, config)
      console.log('API 응답:', response.status, response.statusText)
      
      // 응답 데이터가 비어있는지 확인
      if (!response.data) {
        console.error('API 응답 데이터가 없습니다')
        throw new Error('서버 응답 데이터가 없습니다')
      }
      
      // 응답 처리
      let newPhotos = []
      
      if (Array.isArray(response.data)) {
        console.log(`배열 응답 받음, 개수: ${response.data.length}`)
        newPhotos = response.data.map(photo => ({
          id: photo.photo_id,   // photo_id를 id로 매핑
          image: photo.image,
          image_thumbnail: photo.image_thumbnail || photo.thumbnail_url || photo.image, // 썸네일 URL 추가 (여러 가능한 경로 확인)
          created_at: photo.created_at
        }))
      } else {
        // 단일 객체인 경우
        console.log('단일 객체 응답 받음')
        newPhotos = [{
          id: response.data.photo_id,  // photo_id를 id로 매핑
          image: response.data.image,
          image_thumbnail: response.data.image_thumbnail || response.data.thumbnail_url || response.data.image, // 썸네일 URL 추가 (여러 가능한 경로 확인)
          created_at: response.data.created_at
        }]
      }
      
      console.log(`처리된 사진 데이터:`, newPhotos)
      
      // 기존 일기의 사진 목록 가져오기
      const babyDiary = babyDiaries.value.find(diary => diary.id === diaryId)
      
      if (babyDiary) {
        // 기존 사진 배열과 새 사진 배열 병합
        babyDiary.photos = [...(babyDiary.photos || []), ...newPhotos]
        console.log(`일기 사진 목록 업데이트 완료, 현재 사진 개수: ${babyDiary.photos.length}`)
        
        // 선택된 일기가 있고, 같은 일기라면 선택된 일기의 사진 목록도 업데이트
        if (selectedBabyDiary.value && selectedBabyDiary.value.id === diaryId) {
          selectedBabyDiary.value.photos = [...(selectedBabyDiary.value.photos || []), ...newPhotos]
          console.log('선택된 일기의 사진 목록도 업데이트 완료')
        }
      } else {
        console.log(`일기 ID ${diaryId}를 찾을 수 없음`)
      }
      
      console.log('태교일기 사진 업로드 성공')
      return newPhotos
    } catch (err) {
      console.error('태교일기 사진 업로드 오류:', err)
      
      // 오류 응답이 있는 경우 상세 정보 출력
      if (err.response) {
        console.error('오류 상태:', err.response.status)
        console.error('오류 데이터:', err.response.data)
      }
      
      error.value = '태교일기 사진을 업로드하는 중 오류가 발생했습니다.'
      throw err
    } finally {
      isLoading.value = false
    }
  } 